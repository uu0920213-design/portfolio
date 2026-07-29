from chatbot import chatbot_reply 

print("간단한 챗봇(CMD) - 종료 입력시 종료") 
while True: 
    msg=input("나: ") 
    if msg=="종료": 
        print("챗봇: 이용해 주셔서 감사합니다.") 
        break 
    print("챗봇:", chatbot_reply(msg)) 