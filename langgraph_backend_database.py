from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph.message import add_messages
from dotenv import load_dotenv
from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.tools import tool

load_dotenv()

llm = ChatOpenAI()

#Tools
search_tool = DuckDuckGoSearchRun(region='US-EN')

@tool
def calculator(first_num: float, second_num: float, operation: str) -> dict:
    '''Perform a basic arithmetic operation on two numbers.
    Supported operations: add, subtract, multiply, divide.'''
    try:
        if operation == 'add':
            result = first_num + second_num
        elif operation == 'subtract':
            result = first_num - second_num
        elif operation == 'multiply':
            result = first_num * second_num
        elif operation == 'divide':
            if second_num == 0:
                return {'error': 'Division by zero is not allowed'}
            result = first_num / second_num
        else:
            return {'error': 'Unsupported operation'}
        return {'first_num': first_num, 'second_num': second_num, 'operation': operation, 'result': result}
    except Exception as e:
        return {'error': str(e)}
    
#Make tool list
tools = [search_tool, calculator]

#Make the llm tool aware
llm_with_tools = llm.bind_tools(tools)

# Define State
class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

#Graph node
def chat_node(state: ChatState):
    '''LLM node that may answer or request a tool call'''
    messages = state['messages']
    response = llm_with_tools.invoke(messages)
    return {'messages' : [response]}
tool_node = ToolNode(tools)

#def chat_node(state: ChatState):

    # take user query from state
 #   messages = state['messages']

    #send to llm
  #  response = llm.invoke(messages)

    #response stored in state
   # return {'messages' : [response]}

# Checkpointer
conn = sqlite3.connect(database='chatbot.db', check_same_thread=False)
checkpointer = SqliteSaver(conn = conn)

# Define Graph
graph = StateGraph(ChatState)
#add nodes
graph.add_node('chat_node', chat_node)
graph.add_node('tools', tool_node)

#add edges
graph.add_edge(START, 'chat_node')
graph.add_conditional_edges('chat_node', tools_condition)
graph.add_edge('tools', 'chat_node') 
graph.add_edge('chat_node', END)   

chatbot = graph.compile(checkpointer = checkpointer)

#Helper function to retrieve all threads
def retrive_all_threads():
    all_threads = set()
    for checkpoint in checkpointer.list(None):
        all_threads.add(checkpoint.config['configurable']['thread_id'])

    return list(all_threads)