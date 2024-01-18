import re

from fastapi import HTTPException
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate

from rag_service.config import CLASSIFIER_PROMPT_TEMPLATE
from rag_service.llms.llm import RagLLM
from rag_service.logger import get_logger, Module

logger = get_logger(module=Module.APP)


def classify(question: str) -> bool:
    llm = RagLLM([])
    try:
        chain = LLMChain(
            llm=llm,
            prompt=PromptTemplate.from_template(
                CLASSIFIER_PROMPT_TEMPLATE,
                template_format='jinja2',
            )
        )
        answer = chain.run(
            {
                "question": question
            }
        )
        if re.search("是知识问答", answer):
            return False
        return True
    except Exception:
        raise HTTPException(status_code=500, detail="结果报错，未获取到任何信息")
