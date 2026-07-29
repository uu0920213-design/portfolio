def chatbot_reply(message):
    if "안녕" in message:
        return "안녕하세요!"
    elif "고마워" in message:
        return "별말씀을요!"
    else:
        return "잘 모르겠어요."