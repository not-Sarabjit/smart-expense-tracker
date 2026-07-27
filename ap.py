import streamlit as st
import requests as r

st.title('Tracker')


URL = 'http://127.0.0.1:8000'


try:
    response = r.get(URL + '/health')
    st.text(response.json())
except Exception as e:
    st.text(f'An error occured {e}')
