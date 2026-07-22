import os
import time
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain_huggingface import HuggingFaceEmbeddings


def llm_instance(api_key: str, model_name: str = "llama-3.3-70b-versatile", temperature: float = 0.0) -> ChatGroq:
    """
    Set up the LLM with the provided API key and model name.

    Args:
        api_key (str): The API key for authentication.
        model_name (str): The name of the model to use. Default is "llama-3.3-70b-versatile".
        temperature (float): The temperature setting for the model. Default is 0.0.
    Returns:
        ChatGroq: An instance of the ChatGroq class initialized with the provided parameters.
    """

    return ChatGroq(
        model=model_name,
        api_key=api_key,
        temperature=temperature
    )

def llm_openai_instance(api_key: str, model_name: str = "gpt-4o", temperature: float = 0.0) -> ChatOpenAI:
    """
    Set up the OpenAI LLM with the provided API key and model name.

    Args:
        api_key (str): The API key for authentication.
        model_name (str): The name of the model to use. Default is "gpt-4o".
        temperature (float): The temperature setting for the model. Default is 0.0.
    Returns:
        ChatOpenAI: An instance of the ChatOpenAI class initialized with the provided parameters.
    """

    return ChatOpenAI(
        model=model_name,
        openai_api_key=api_key,
        temperature=temperature
    )

def embedding_instance(model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> HuggingFaceEmbeddings:
    """
    Set up the embedding model with the provided model name.

    Args:
        model_name (str): The name of the embedding model to use. Default is "sentence-transformers/all-MiniLM-L6-v2".
    Returns:
        HuggingFaceEmbeddings: An instance of the HuggingFaceEmbeddings class.
    """
    return HuggingFaceEmbeddings(model_name=model_name)