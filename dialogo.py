from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
#from langchain-ibm import Model
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
# For State Graph
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




def dialogo(material:str):

    generate_prompt = PromptTemplate(
        template="""

        <|begin_of_text|>

        <|start_header_id|>system<|end_header_id|>
        You are an AI assistant for friendly English classes, your task is to review the structure of each section of an English class and you must create the English dialogue that the teacher must say to lead each section of the class.
        In your answer you must return only the dialogue that a teacher must say completely in English to lead each section.

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


    dialogo_asistente=sql_chain.invoke({"material":material})
    #print(resultado)
    return dialogo_asistente