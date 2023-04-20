import os
import platform
import ast
import openai
from langchain import OpenAI, SQLDatabase, SQLDatabaseChain,PromptTemplate
import pandas as pd
import streamlit as st
from streamlit_chat import message
from sqlalchemy import create_engine
from openai.error import RateLimitError

openai.api_key=st.secrets.__getitem__("OPENAI_API_KEY")
llm = OpenAI(temperature=0.3,model_name='text-davinci-003',max_retries=0)
_DEFAULT_TEMPLATE = """Given an input question, first create a syntactically correct {dialect} query to run, then look at the results of the query and return the answer. Never return more than 5 rows
Use the following format:

Question: "Question here"
SQLQuery: "SQL Query to run"
SQLResult: "Result of the SQLQuery"
Answer: "Final answer here"

Only use the following tables:

{table_info}

Question: {input}"""
PROMPT = PromptTemplate(
        input_variables=["input", "table_info", "dialect"], template=_DEFAULT_TEMPLATE
        
)
db = SQLDatabase.from_uri("sqlite:///data.db")
conn=create_engine("sqlite:///data.db")
db_chain = SQLDatabaseChain(llm=llm, database=db, prompt=PROMPT, verbose=True, return_intermediate_steps=True)

def generate_response(user_input,db_chain=db_chain):
    
    try:
        result=db_chain(user_input)

        query=result['intermediate_steps'][0]

        data=pd.DataFrame.from_records(ast.literal_eval(result['intermediate_steps'][1]))

        answer=result['result']

        return query,data,answer
    except RateLimitError:
        return 'No query generated',None,"No credit"



if __name__=="__main__":
    if 'generated' not in st.session_state:
        st.session_state['generated'] = []
    if 'past' not in st.session_state:
        st.session_state['past'] = []

    if 'sql' not in st.session_state:
        st.session_state['sql'] = []

    
    
    # container for chat history
response_container = st.container()
# container for text box
container = st.container()
sql_container=st.container()
with container:
    with st.form(key='my_form', clear_on_submit=True):
        user_input = st.text_area("You:", key='input', height=100)
        submit_button = st.form_submit_button(label='Send')

    if submit_button and user_input:
        query,data,answer = generate_response(user_input)
        st.session_state['past'].append(user_input)
        st.session_state['generated'].append(answer)
        st.session_state['sql'].append(query)

        if st.session_state['generated']:
            with response_container:
                for i in range(len(st.session_state['generated'])):
                    message(st.session_state["past"][i], is_user=True, key=str(i) + '_user',avatar_style='adventurer')
                    message(st.session_state["generated"][i], key=str(i),avatar_style='bottts')


            with sql_container:
                if submit_button and user_input:
                    
                    st.sidebar.code(st.session_state["sql"][i])
                    try:
                        st.sidebar.dataframe(pd.read_sql(con=conn,sql=query))
                    except:
                        st.sidebar.write("No data to show")


    clear_button = st.button("Clear Conversation", key="clear")
    if clear_button:
        st.session_state['generated'] = []
        st.session_state['past'] = []
        st.session_state['sql'] = []
        st.session_state['messages'] = [
            {"role": "system", "content": "You are a helpful assistant."}
        ]
