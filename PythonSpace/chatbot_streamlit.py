import streamlit as st 
from chatbot import chatbot_reply 
st.title("🤔 간단한 챗봇") 
msg=st.text_input("메시지") 
if st.button("보내기"): 
    if msg.strip(): 
        st.success(chatbot_reply(msg)) 
    else: 
        st.warning("메시지를 입력하세요.")