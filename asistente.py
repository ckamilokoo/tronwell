from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
#from langchain-ibm import Model
from ibm_watson_machine_learning.foundation_models import Model
from ibm_watson_machine_learning.foundation_models.utils.enums import ModelTypes
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
# For State Graph
from typing_extensions import TypedDict
import os
# Generation Prompt
from langchain_ibm import WatsonxLLM

llama_3_model = WatsonxLLM(
    model_id="meta-llama/llama-3-70b-instruct",
    url="https://us-south.ml.cloud.ibm.com",
    apikey="0GY8cqsa49R8Gs6aiK0RB5Hb6ZRDFyKew474yYfVJBKa",
    project_id="37e2e673-598a-4dca-af77-b102ee3b47c9",
    params={
  "decoding_method": "greedy",
  "max_new_tokens": 4096,
  "min_new_tokens": 0,
  "stop_sequences": [
   ";"
  ],
  "repetition_penalty": 1
 },
    )




def clase_virtual(material:str):

    generate_prompt = PromptTemplate(
        template="""

        <|begin_of_text|>

        <|start_header_id|>system<|end_header_id|>

        You are a friendly and focused English class AI assistant, your task is to create a class structure based on content that you must use as material to design the class.
        In your answer you must create a class structure in 3 parts.
        introduction to the class, objectives of the class, teaching content of the class that corresponds to the material you will be given, exercises of the material covered in the class and closing.


        <|eot_id|>

        <|start_header_id|>user<|end_header_id|>

        material: {material}
        Answer:

        <|eot_id|>

        <|start_header_id|>assistant<|end_header_id|>""",
        input_variables=["material"],
    )

    # Chain
    sql_chain = generate_prompt | llama_3_model | StrOutputParser()


    resultado=sql_chain.invoke({"material":material})
    #print(resultado)
    return resultado