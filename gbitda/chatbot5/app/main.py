
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

import joblib
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

from app.course_recommender import recommend_courses
from app.auth import make_auth_router
from app.estate import service as estate_service
from app.estate.router import make_router
from app.estate.store import EstateStore


# ==========================================
# 1. 프로젝트 경로 및 머신러닝 모델
# ==========================================
BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = BASE_DIR / "models" / "intent_model.joblib"

intent_model = joblib.load(MODEL_PATH)


# ==========================================
# 2. FastAPI 설정
# ==========================================
app = FastAPI(title="집이있다 AI 챗봇")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:5501",
        "http://localhost:5501",
        *[o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()],
    ],
    # 같은 공유기/사내망(192.168.x.x, 10.x.x.x 등)의 PC 에서 IP 주소로 열어도 챗봇이 동작하도록 허용
    allow_origin_regex=r"^http://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+|172\.(1[6-9]|2\d|3[01])\.\d+\.\d+)(:\d+)?$",
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


# ==========================================
# 3. MongoDB 연결
# ==========================================
client = MongoClient(
    os.getenv("MONGO_URI", "mongodb://localhost:27017/"),
    serverSelectionTimeoutMS=2000,
)

db = client[os.getenv("MONGO_DB", "gbitda")]

chat_collection = db["chat_history"]
chat_sessions = db["chat_sessions"]

# 부동산 분석 (실거래 조회 · 월별 통계 · 예상 매매가)
estate_store = EstateStore(db)
app.include_router(make_router(estate_store))

# 회원가입 · 로그인 (users, auth_sessions 컬렉션)
app.include_router(make_auth_router(db))


@app.on_event("startup")
def check_mongodb_connection():
    try:
        client.admin.command("ping")
        print("MongoDB 연결 성공!")
        print("데이터베이스: gbitda")
        print("컬렉션: chat_history, chat_sessions, estate_*")
    except Exception as e:
        print("MongoDB 연결 실패:", e)
    try:
        print("부동산 데이터:", estate_store.status())   # 첫 질문이 느려지지 않도록 미리 로드
    except Exception as e:
        print("부동산 데이터 로드 실패:", e)


# ==========================================
# 4. 요청 데이터
# ==========================================
class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    conversation_id: Optional[str] = None


# ==========================================
# 5. 상담방 생성 또는 기존 상담방 찾기
# ==========================================
def get_or_create_session(
    conversation_id: Optional[str],
    message: str,
) -> str:
    now = datetime.now(timezone.utc)

    # 기존 상담방이 전달된 경우 해당 상담방 사용
    if conversation_id:
        try:
            session_id = ObjectId(conversation_id)
        except (InvalidId, TypeError):
            raise HTTPException(
                status_code=400,
                detail="올바르지 않은 상담 ID입니다.",
            )

        session = chat_sessions.find_one({"_id": session_id})

        if not session:
            raise HTTPException(
                status_code=404,
                detail="상담 기록을 찾을 수 없습니다. 새 상담을 시작해 주세요.",
            )

        chat_sessions.update_one(
            {"_id": session_id},
            {
                "$set": {
                    "updated_at": now,
                    "is_read": False,
                }
            },
        )

        return str(session_id)

    # conversation_id가 없으면 새 상담방 생성
    result = chat_sessions.insert_one({
        "title": message[:40] or "새 상담",
        "created_at": now,
        "updated_at": now,
        "is_read": False,
    })

    return str(result.inserted_id)


# ==========================================
# 6. 질문 유형에 따른 답변 및 강의 추천
# ==========================================
def make_response(intent, message):
    recommendation_words = [
        "추천",
        "강의",
        "클래스",
        "수강",
        "배우고 싶",
        "배우려면",
        "교육 과정",
    ]

    wants_recommendation = any(
        word in message for word in recommendation_words
    )

    # 강의 추천
    if intent == "course_recommend" or (
        intent == "auction" and wants_recommendation
    ):
        results = recommend_courses(message)
        courses = []

        for item in results:
            course = item["course"]

            courses.append({
                "id": course["id"],
                "name": course["name"],
                "category": course["category"],
                "price": course["price"],
                "description": course["description"],
                "url": course["url"],
                "matched_keywords": item["matched_keywords"],
            })

        if courses:
            text = "질문과 관련된 강의를 찾아봤어요."
        else:
            text = (
                "관련 강의를 찾지 못했어요. "
                "내집마련, 부동산기초, 1Day, 경매 중 "
                "관심 분야를 알려주세요."
            )

        return {
            "text": text,
            "courses": courses,
        }

    # 실거래가 분석
    if intent == "price_analysis":
        return {
            "text": (
                "아파트 실거래가 분석을 도와드릴게요. "
                "분석할 지역과 아파트 이름을 알려주세요."
            ),
            "courses": [],
        }

    # 부동산 기초
    if intent == "real_estate_basic":
        return {
            "text": (
                "부동산 기초부터 차근차근 알아볼게요. "
                "궁금한 용어나 개념을 질문해 주세요."
            ),
            "courses": [],
        }

    # 경매
    if intent == "auction":
        return {
            "text": (
                "경매 학습을 도와드릴게요. "
                "말소기준권리, 권리분석, 입찰 절차 중 "
                "궁금한 내용을 질문해 주세요."
            ),
            "courses": [],
        }

    # 기타 질문
    return {
        "text": (
            "집이있다 AI 상담입니다. "
            "강의 신청이나 수강 안내를 질문해 주세요."
        ),
        "courses": [],
    }


# ==========================================
# 7. 서버 확인
# ==========================================
@app.get("/")
def home():
    return {
        "message": "집이있다 AI 챗봇 서버가 실행 중입니다."
    }


# ==========================================
# 8. 챗봇 질문 처리
# ==========================================
@app.post("/chat")
def chat(request: ChatRequest):
    user_message = request.message.strip()

    if not user_message:
        raise HTTPException(
            status_code=400,
            detail="질문을 입력해 주세요.",
        )

    # 상담방 생성 또는 기존 상담방 연결
    conversation_id = get_or_create_session(
        request.conversation_id,
        user_message,
    )

    # 부동산 가격 질문이면 실거래 분석/예측으로 답변, 아니면 기존 흐름
    estate = None
    session_doc = chat_sessions.find_one({"_id": ObjectId(conversation_id)}) or {}
    try:
        est = estate_service.answer(
            estate_store, user_message, session_doc.get("estate_context")
        )
    except Exception as e:
        print("부동산 분석 실패:", repr(e))
        est = None

    if est:
        intent = "price_analysis"
        answer = {"text": est["text"], "courses": []}
        estate = est["estate"]
        chat_sessions.update_one(
            {"_id": ObjectId(conversation_id)},
            {"$set": {"estate_context": est["context"]}},
        )
    else:
        # 머신러닝으로 질문 유형 예측
        intent = str(intent_model.predict([user_message])[0])

        # 답변 및 추천 강의 생성
        answer = make_response(intent, user_message)

    now = datetime.now(timezone.utc)
    history_saved = False

    try:
        chat_collection.insert_one({
            "conversation_id": conversation_id,
            "user_message": user_message,
            "intent": intent,
            "bot_response": answer["text"],
            "recommended_courses": answer["courses"],
            "estate": estate,
            "timestamp": now,
        })

        history_saved = True
        print("채팅 기록 저장 성공!")

    except Exception as e:
        print("MongoDB 채팅 기록 저장 실패:", e)

    return {
        "conversation_id": conversation_id,
        "user_message": user_message,
        "intent": intent,
        "bot_response": answer["text"],
        "recommended_courses": answer["courses"],
        "estate": estate,
        "history_saved": history_saved,
    }


# ==========================================
# 9. 상담 목록 조회
# ==========================================
@app.get("/sessions")
def get_sessions():
    sessions = chat_sessions.find().sort("updated_at", -1)

    result = []

    for session in sessions:
        conversation_id = str(session["_id"])

        # 해당 상담방의 마지막 메시지 가져오기
        last_chat = chat_collection.find_one(
            {"conversation_id": conversation_id},
            sort=[("timestamp", -1)],
        )

        if last_chat:
            last_user_message = last_chat.get("user_message", "")
            last_bot_response = last_chat.get("bot_response", "")
            last_message = last_user_message
        else:
            last_user_message = ""
            last_bot_response = ""
            last_message = "새로운 상담을 시작해 보세요."

        created_at = session.get("created_at")
        updated_at = session.get("updated_at")

        result.append({
            "conversation_id": conversation_id,
            "title": session.get("title", "집이잇다 AI 상담봇"),
            "last_message": last_message,
            "last_user_message": last_user_message,
            "last_bot_response": last_bot_response,
            "is_read": session.get("is_read", False),
            "created_at": (
                created_at.isoformat() if created_at else None
            ),
            "updated_at": (
                updated_at.isoformat() if updated_at else None
            ),
        })

    return result


# ==========================================
# 10. 특정 상담의 전체 기록 조회
# ==========================================
@app.get("/sessions/{conversation_id}")
def get_session_history(conversation_id: str):
    try:
        session_id = ObjectId(conversation_id)
    except (InvalidId, TypeError):
        raise HTTPException(
            status_code=400,
            detail="올바르지 않은 상담 ID입니다.",
        )

    session = chat_sessions.find_one({"_id": session_id})

    if not session:
        raise HTTPException(
            status_code=404,
            detail="상담 기록을 찾을 수 없습니다.",
        )

    messages = chat_collection.find(
        {"conversation_id": conversation_id}
    ).sort("timestamp", 1)

    return {
        "conversation_id": conversation_id,
        "title": session.get("title", "새 상담"),
        "is_read": session.get("is_read", False),
        "messages": [
            {
                "user_message": item.get("user_message", ""),
                "bot_response": item.get("bot_response", ""),
                "intent": item.get("intent"),
                "recommended_courses": item.get(
                    "recommended_courses", []
                ),
                "estate": item.get("estate"),
                "timestamp": (
                    item["timestamp"].isoformat()
                    if item.get("timestamp")
                    else None
                ),
            }
            for item in messages
        ],
    }


# ==========================================
# 11. 상담방 읽음 처리
# ==========================================
@app.patch("/sessions/read-all")
def mark_all_sessions_read():
    chat_sessions.update_many(
        {},
        {
            "$set": {
                "is_read": True,
            }
        },
    )

    return {
        "success": True,
        "message": "모든 상담을 읽음 처리했습니다.",
    }


@app.patch("/sessions/{conversation_id}/read")
def mark_session_read(conversation_id: str):
    try:
        session_id = ObjectId(conversation_id)
    except (InvalidId, TypeError):
        raise HTTPException(
            status_code=400,
            detail="올바르지 않은 상담 ID입니다.",
        )

    result = chat_sessions.update_one(
        {"_id": session_id},
        {
            "$set": {
                "is_read": True,
            }
        },
    )

    if result.matched_count == 0:
        raise HTTPException(
            status_code=404,
            detail="상담 기록을 찾을 수 없습니다.",
        )

    return {
        "success": True,
        "message": "상담을 읽음 처리했습니다.",
    }


# ==========================================
# 12. 특정 상담방 삭제
# ==========================================
@app.delete("/sessions/{conversation_id}")
def delete_session(conversation_id: str):
    try:
        session_id = ObjectId(conversation_id)
    except (InvalidId, TypeError):
        raise HTTPException(
            status_code=400,
            detail="올바르지 않은 상담 ID입니다.",
        )

    session = chat_sessions.find_one({"_id": session_id})

    if not session:
        raise HTTPException(
            status_code=404,
            detail="상담 기록을 찾을 수 없습니다.",
        )

    # 선택한 상담방의 메시지만 삭제
    chat_collection.delete_many({
        "conversation_id": conversation_id
    })

    # 선택한 상담방 정보 삭제
    chat_sessions.delete_one({
        "_id": session_id
    })

    return {
        "success": True,
        "message": "대화 기록이 삭제되었습니다.",
        "conversation_id": conversation_id,
    }


# ==========================================
# 13. 모든 상담 기록 삭제
# ==========================================
@app.delete("/sessions")
def delete_all_sessions():
    # 메시지와 상담방을 모두 삭제
    chat_collection.delete_many({})
    chat_sessions.delete_many({})

    return {
        "success": True,
        "message": "모든 대화 기록이 삭제되었습니다.",
    }
