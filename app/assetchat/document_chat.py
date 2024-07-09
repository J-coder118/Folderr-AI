from assetchat.common import (
    POSTGRES_CONNECTION_STRING,
    get_collection_name,
    get_vector_store,
)
from assetchat.models import Prompt
from django.conf import settings
from langchain import PromptTemplate
from langchain.chains import ConversationalRetrievalChain
from langchain.chat_models import ChatOpenAI
from langchain.memory import (
    ConversationSummaryBufferMemory,
    SQLChatMessageHistory,
)


def get_question_generator_template():
    prompt_text = Prompt.objects.get(
        prompt_type=Prompt.QUESTION_GENERATOR, default=True
    )
    return PromptTemplate(
        template=prompt_text.content,
        input_variables=["question", "chat_history"],
    )


def get_question_answering_template():
    prompt_text = Prompt.objects.get(
        prompt_type=Prompt.QUESTION_ANSWERING, default=True
    )
    return PromptTemplate(
        template=prompt_text.content, input_variables=["context", "question"]
    )


def get_chat_history(session_id):
    return SQLChatMessageHistory(
        connection_string=POSTGRES_CONNECTION_STRING,
        session_id=session_id,
        table_name="langchain_chat_history",
    )


def answer_question(question, folder, session_id, temperature: float):
    vector_store = get_vector_store(get_collection_name(folder))
    llm = ChatOpenAI(
        temperature=temperature,
        openai_api_key=settings.OPENAI_SECRET_KEY,
    )
    chat_history = get_chat_history(session_id)
    qa = ConversationalRetrievalChain.from_llm(
        llm,
        vector_store.as_retriever(),
        memory=ConversationSummaryBufferMemory(
            memory_key="chat_history",
            llm=llm,
            chat_memory=chat_history,
            return_messages=True,
        ),
        condense_question_prompt=get_question_generator_template(),
        combine_docs_chain_kwargs={
            "prompt": get_question_answering_template()
        },
    )
    result = qa({"question": question, "chat_history": chat_history.messages})
    answer = result["answer"]
    chat_history.add_user_message(question)
    chat_history.add_ai_message(answer)
    return result
