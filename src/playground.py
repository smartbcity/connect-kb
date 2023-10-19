import json
import os
import time

from dotenv import load_dotenv
from langchain.agents import AgentType
from langchain.agents import initialize_agent
from langchain.chat_models import ChatOpenAI, ChatAnthropic
from langchain.document_loaders import PyPDFium2Loader as PdfReader
from langchain.embeddings import OpenAIEmbeddings
from langchain.graphs import Neo4jGraph
from langchain.tools import WriteFileTool, Tool

from services.extractor.cccev_extractor import MethodologyEligibilityCccevExtractor
from services.graph.document_repository import DocumentRepository
from services.graph.graph_embedder import GraphEmbedder, INDEX_EMBEDDED, PROPERTY_EMBED_TEXT
from services.graph.tool_graph import QuestionGraphTool, QueryGraphTool
from cccev.model.cccev import CCCEV

DIR_DATA = "data"
DIR_OUTPUT = f"{DIR_DATA}/output"
DIR_INPUT = f"{DIR_DATA}/input"

FILE_CCP = "CCP-Book-R2-FINAL-26Jul23.pdf"
FILE_VM003 = "VM0003-IFM-Through-Extension-Of-Rotation-Age-v1.3.pdf"
FILE_VM003_MD = "VM0003-IFM-Through-Extension-Of-Rotation-Age-v1.3.md"

load_dotenv()
GPT4 = ChatOpenAI(temperature=0, model_name="gpt-4")
GPT3 = ChatOpenAI(temperature=0, model_name="gpt-3.5-turbo")
ANTHROPIC = ChatAnthropic(temperature=0, model="claude-2")
LLM = GPT4

GRAPH = Neo4jGraph(url="neo4j://localhost:7687", username="neo4j", password="smartbsmartb")
EMBEDDER = OpenAIEmbeddings()


def question_graph(question: str) -> str:
    # question_embedding = EMBEDDER.embed_query(question)
    # answer_context_parts = GRAPH.query("""
    #     CALL db.index.vector.queryNodes('embeddingIndex', 20, $question_embedding)
    #     YIELD node, score
    #     RETURN node.text AS text, score
    # """, {"question_embedding": question_embedding})
    #
    # answer_context = '\n'.join(map(lambda context_part: context_part["text"], answer_context_parts))
    agent = initialize_agent(
        tools=[
            QuestionGraphTool(EMBEDDER, GRAPH),
            QueryGraphTool(LLM, GRAPH)
        ],
        llm=LLM,
        agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True,
        max_iterations=None,
        max_execution_time=None
    )

    prompt = f"""
    You are an intelligent chatbot. Please answer the question as truly as possible, and using only the context you are able to fetch from the knowledge graph. 
    You are allowed to question the graph multiple times.
    Even if the question seems vague or unclear, you must always question the graph at least once. In the question of a vague or unclear question, start with the QuestionGraph tool
    If you can’t find answer from the context, simplay say “Sorry I don’t have enough context for your question.”
    Question: {question}
    """
    # answer = GPT3.predict(prompt)
    print(prompt)
    answer = agent.run(prompt)
    print(answer)
    return answer


# cccev = """{"dataUnits": [{"identifier": "xsdString", "name": "XSDString", "description": "Any string of characters", "type": "STRING"}, {"identifier": "xsdBoolean", "name": "XSDBoolean", "description": "True or false", "type": "BOOLEAN"}, {"identifier": "xsdDate", "name": "XSDDate", "description": "A date", "type": "DATE"}], "informationConcepts": [{"identifier": "forestManagementPractices", "name": "Forest Management Practices", "description": "The practices used to manage the forest, such as harvesting techniques", "unit": "xsdString", "question": "What are the forest management practices used?", "source": "VM0003-IFM-Through-Extension-Of-Rotation-Age-v1.3.pdf page 5"}, {"identifier": "projectAreaCondition", "name": "Project Area Condition", "description": "The condition that the project area must meet prior to the first verification event", "unit": "xsdString", "question": "What condition does the project area meet?", "source": "VM0003-IFM-Through-Extension-Of-Rotation-Age-v1.3.pdf page 5"}, {"identifier": "projectLength", "name": "Project Length", "description": "The minimum length of the project as defined in the project description", "unit": "xsdDate", "question": "What is the minimum project length?", "source": "VM0003-IFM-Through-Extension-Of-Rotation-Age-v1.3.pdf page 5"}, {"identifier": "fireControlMeasures", "name": "Fire Control Measures", "description": "The measures taken to control fire in the project area", "unit": "xsdString", "question": "What fire control measures are taken?", "source": "VM0003-IFM-Through-Extension-Of-Rotation-Age-v1.3.pdf page 6"}, {"identifier": "leakagePrevention", "name": "Leakage Prevention", "description": "The measures taken to prevent leakage through activity shifting to other lands", "unit": "xsdBoolean", "question": "Are there measures to prevent leakage?", "source": "VM0003-IFM-Through-Extension-Of-Rotation-Age-v1.3.pdf page 6"}, {"identifier": "projectStartDate", "name": "Project Start Date", "description": "The start date of the project", "unit": "xsdDate", "question": "What is the start date of the project?", "source": "VM0003-IFM-Through-Extension-Of-Rotation-Age-v1.3.pdf page 5"}, {"identifier": "methodology", "name": "Methodology", "description": "The methodology used for the project", "unit": "xsdString", "question": "What methodology is used for the project?", "source": "VM0003-IFM-Through-Extension-Of-Rotation-Age-v1.3.pdf page 4"}, {"identifier": "timberHarvesting", "name": "Timber Harvesting", "description": "Whether the forest is subject to timber harvesting in the baseline scenario", "unit": "xsdBoolean", "question": "Is the forest subject to timber harvesting in the baseline scenario?", "source": "VM0003-IFM-Through-Extension-Of-Rotation-Age-v1.3.pdf page 5"}], "requirements": [{"identifier": "projectEligibility", "name": "Project Eligibility", "description": "The project must involve an extension in rotation age (ERA) and must not encompass managed peat forests. The project area must meet one of the specified conditions prior to the first verification event. The project must have a defined start date.", "hasRequirement": [], "hasConcepts": ["forestManagementPractices", "projectAreaCondition", "projectStartDate", "methodology", "timberHarvesting"], "source": "VM0003-IFM-Through-Extension-Of-Rotation-Age-v1.3.pdf page 5"}, {"identifier": "fireControl", "name": "Fire Control", "description": "If fire is used as part of forest management, fire control measures must be taken to ensure fire does not spread outside the project area.", "hasRequirement": [], "hasConcepts": ["fireControlMeasures"], "source": "VM0003-IFM-Through-Extension-Of-Rotation-Age-v1.3.pdf page 6"}, {"identifier": "leakagePrevention", "name": "Leakage Prevention", "description": "There must be no leakage through activity shifting to other lands owned or managed by project proponents outside the boundary of the project area.", "hasRequirement": [], "hasConcepts": ["leakagePrevention"], "source": "VM0003-IFM-Through-Extension-Of-Rotation-Age-v1.3.pdf page 6"}, {"identifier": "projectStartDate", "name": "Project Start Date", "description": "The project must have a defined start date.", "hasRequirement": [], "hasConcepts": ["projectStartDate"], "source": "VM0003-IFM-Through-Extension-Of-Rotation-Age-v1.3.pdf page 5"}], "document": "VM0003-IFM-Through-Extension-Of-Rotation-Age-v1.3.pdf"}"""


def compute_session_id(iteration: int) -> str:
    return f"kb_{iteration}_"


def extract_cccev(input_file_path: str, iteration: int) -> CCCEV:
    reader = PdfReader(input_file_path)
    pages = reader.load()
    text = f"""
Document: {input_file_path.rpartition("/")[-1]}
Page 4: {pages[4 - 1].page_content}
---
Page 5: {pages[5 - 1].page_content}
---
Page 6: {pages[6 - 1].page_content}
"""

    cccev = MethodologyEligibilityCccevExtractor(LLM).extract(
        text=text,
        session_id=compute_session_id(iteration)
    )

    WriteFileTool().run({
        "file_path": f"{DIR_OUTPUT}/result-cccev-parser-{iteration}.json",
        "text": json.dumps(cccev, default=lambda o: o.__dict__)
    })
    return cccev


def disambiguate(node_label: str, iteration: int):
    session_id = compute_session_id(iteration)

    nodes = GRAPH.query(f"""
        MATCH (du:{node_label})
        WHERE du.identifier STARTS WITH $session_id
        RETURN du.identifier as identifier, du.name as name, du.description as description, du.type as type
    """, {"session_id": session_id})

    for node in nodes:
        node_text = GraphEmbedder.node_to_text(node_label, node)
        node_embedding = EMBEDDER.embed_query(node_text)
        search_result_parts = GRAPH.query(f"""
            CALL db.index.vector.queryNodes('{INDEX_EMBEDDED}', 20, $node_embedding) 
            YIELD node, score
            WHERE node.identifier <> $node_identifier
            RETURN node.{PROPERTY_EMBED_TEXT} AS text
        """, {"node_embedding": node_embedding, "node_identifier": node["identifier"]})

        search_result = '\n'.join(map(lambda context_part: context_part["text"], search_result_parts))

        disambiguation_prompt = f"""You are a disambiguation tool.
            Your task is to identify if the given node is a duplication of any other nodes of the given graph. 
            A node is considered a duplication if it represents the same entity as another one, based on its name, description and type. 
            The final result must be the identifier of the duplicated node in the graph, or None if there is no duplication or if there is no graph data.
            Your response will be used as-is in a program inside a string variable, so you must not say anything else than the answer and not add any formatting (e.g. do not wrap it with quotes).
            If you find that multiple nodes are duplicated, return the most relevant one.
            Node: {node_text}
            Graph: {search_result}
        """
        duplicated_identifier = GPT4.predict(disambiguation_prompt)

        if duplicated_identifier != "None":
            print(f"""{node["identifier"]} -> {duplicated_identifier}""")
            GRAPH.query(f"""
                MATCH (original:{node_label})
                WHERE original.identifier = $original
                MATCH (duplicate:{node_label})
                WHERE duplicate.identifier = $duplicate
                CALL apoc.refactor.mergeNodes([original, duplicate], {{properties:"discard", mergeRels:true}})
                YIELD node
                RETURN node
            """, {"original": duplicated_identifier, "duplicate": node["identifier"]})
        else:
            print(f"""No duplication for {node["identifier"]}""")


def tool_question(question: str):
    vector = EMBEDDER.embed_query(question)
    return "\n".join(DocumentRepository(GRAPH).find_similar_chunks([f"{DIR_INPUT}/{FILE_VM003}"], vector, 5))


if __name__ == '__main__':
    if not os.path.exists(DIR_OUTPUT):
        os.makedirs(DIR_OUTPUT)

    iteration = 39
    # cccev = """{"dataUnits":[{"identifier":"kb_31_xsdString","name":"XSDString","description":"Any string of characters","type":"STRING","status":"EXISTS"},{"identifier":"kb_31_xsdBoolean","name":"XSDBoolean","description":"True or false","type":"BOOLEAN","status":"EXISTS"}],"informationConcepts":[{"identifier":"kb_31_forestManagementPractices","name":"Forest Management Practices","description":"The practices used to manage a forest","unit":"kb_31_xsdString","question":"What are the forest management practices used in the project?","status":"EXISTS","source":"VM0003-IFM-Through-Extension-Of-Rotation-Age-v1.3.pdf - Page 4"},{"identifier":"kb_31_projectType","name":"Project Type","description":"The type of the project","unit":"kb_31_xsdString","question":"What is the type of the project?","status":"EXISTS","source":"VM0003-IFM-Through-Extension-Of-Rotation-Age-v1.3.pdf - Page 5"},{"identifier":"kb_31_harvestingTechniques","name":"Harvesting Techniques","description":"The harvesting techniques used in the project","unit":"kb_31_xsdString","question":"What are the harvesting techniques used in the project?","status":"EXISTS","source":"VM0003-IFM-Through-Extension-Of-Rotation-Age-v1.3.pdf - Page 5"},{"identifier":"kb_31_forestCertification","name":"Forest Certification","description":"The certification status of the forest","unit":"kb_31_xsdString","question":"What is the certification status of the forest?","status":"EXISTS","source":"VM0003-IFM-Through-Extension-Of-Rotation-Age-v1.3.pdf - Page 5"},{"identifier":"kb_31_projectLength","name":"Project Length","description":"The minimum length of the project","unit":"kb_31_xsdString","question":"What is the minimum length of the project?","status":"EXISTS","source":"VM0003-IFM-Through-Extension-Of-Rotation-Age-v1.3.pdf - Page 5"},{"identifier":"kb_31_peatForestPresence","name":"Peat Forest Presence","description":"Whether the project encompasses managed peat forests","unit":"kb_31_xsdBoolean","question":"Does the project encompass managed peat forests?","status":"EXISTS","source":"VM0003-IFM-Through-Extension-Of-Rotation-Age-v1.3.pdf - Page 6"},{"identifier":"kb_31_managementPracticesProjection","name":"Management Practices Projection","description":"The projection of management practices in both with- and without-project scenarios","unit":"kb_31_xsdString","question":"What is the projection of management practices in both with- and without-project scenarios?","status":"EXISTS","source":"VM0003-IFM-Through-Extension-Of-Rotation-Age-v1.3.pdf - Page 6"},{"identifier":"kb_31_fireControlMeasures","name":"Fire Control Measures","description":"The fire control measures taken in the project","unit":"kb_31_xsdString","question":"What are the fire control measures taken in the project?","status":"EXISTS","source":"VM0003-IFM-Through-Extension-Of-Rotation-Age-v1.3.pdf - Page 6"},{"identifier":"kb_31_leakagePrevention","name":"Leakage Prevention","description":"Whether there is leakage prevention through activity shifting to other lands","unit":"kb_31_xsdBoolean","question":"Is there leakage prevention through activity shifting to other lands?","status":"EXISTS","source":"VM0003-IFM-Through-Extension-Of-Rotation-Age-v1.3.pdf - Page 6"}],"requirements":[{"identifier":"kb_31_improveForestManagement","name":"Improve Forest Management","kind":"CRITERION","description":"The project must involve improving forest management practices to increase the carbon stock on land by extending the rotation age of a forest or patch of forest before harvesting.","hasRequirement":[],"hasConcepts":["kb_31_forestManagementPractices"],"status":"CREATED","source":"VM0003-IFM-Through-Extension-Of-Rotation-Age-v1.3.pdf - Page 4"},{"identifier":"kb_31_ifmProjectActivity","name":"IFM Project Activity","kind":"CRITERION","description":"The project must be an Improved Forest Management (IFM) project activity that involves an extension in rotation age (ERA).","hasRequirement":[],"hasConcepts":["kb_31_projectType"],"status":"CREATED","source":"VM0003-IFM-Through-Extension-Of-Rotation-Age-v1.3.pdf - Page 5"},{"identifier":"kb_31_harvestingTechniquesRequirement","name":"Harvesting Techniques Requirement","kind":"CRITERION","description":"Forest management in both baseline and project scenarios must involve harvesting techniques such as clear cuts, patch cuts, seed trees, continuous thinning, or group selection practices.","hasRequirement":[],"hasConcepts":["kb_31_harvestingTechniques"],"status":"CREATED","source":"VM0003-IFM-Through-Extension-Of-Rotation-Age-v1.3.pdf - Page 5"},{"identifier":"kb_31_forestCertificationRequirement","name":"Forest Certification Requirement","kind":"CRITERION","description":"Prior to the first verification event, the project area must be either certified by Forest Stewardship Council (FSC); or subject to an easement, or equivalent instrument, recorded against the deed of property that prohibits commercial harvesting for the duration of the crediting period unless later certified by FSC.","hasRequirement":[],"hasConcepts":["kb_31_forestCertification"],"status":"CREATED","source":"VM0003-IFM-Through-Extension-Of-Rotation-Age-v1.3.pdf - Page 5"},{"identifier":"kb_31_projectLengthRequirement","name":"Project Length Requirement","kind":"CRITERION","description":"Project proponents must define the minimum project length in the project description.","hasRequirement":[],"hasConcepts":["kb_31_projectLength"],"status":"CREATED","source":"VM0003-IFM-Through-Extension-Of-Rotation-Age-v1.3.pdf - Page 5"},{"identifier":"kb_31_peatForestPresenceRequirement","name":"Peat Forest Presence Requirement","kind":"CRITERION","description":"The project must not encompass managed peat forests, and the proportion of wetlands is not expected to change as part of the project.","hasRequirement":[],"hasConcepts":["kb_31_peatForestPresence"],"status":"CREATED","source":"VM0003-IFM-Through-Extension-Of-Rotation-Age-v1.3.pdf - Page 6"},{"identifier":"kb_31_managementPracticesProjectionRequirement","name":"Management Practices Projection Requirement","kind":"CRITERION","description":"Project proponents must have a projection of management practices in both with- and without-project scenarios.","hasRequirement":[],"hasConcepts":["kb_31_managementPracticesProjection"],"status":"CREATED","source":"VM0003-IFM-Through-Extension-Of-Rotation-Age-v1.3.pdf - Page 6"},{"identifier":"kb_31_fireControlMeasuresRequirement","name":"Fire Control Measures Requirement","kind":"CRITERION","description":"Where fire is used as part of forest management, fire control measures such as installation of firebreaks or back-burning must be taken to ensure fire does not spread outside the project area — that is, no biomass burning is permitted to occur beyond the project area due to forest management activities.","hasRequirement":[],"hasConcepts":["kb_31_fireControlMeasures"],"status":"CREATED","source":"VM0003-IFM-Through-Extension-Of-Rotation-Age-v1.3.pdf - Page 6"},{"identifier":"kb_31_leakagePreventionRequirement","name":"Leakage Prevention Requirement","kind":"CRITERION","description":"There must be no leakage through activity shifting to other lands owned or managed by project proponents outside the boundary of the project area.","hasRequirement":[],"hasConcepts":["kb_31_leakagePrevention"],"status":"CREATED","source":"VM0003-IFM-Through-Extension-Of-Rotation-Age-v1.3.pdf - Page 6"}],"document":{"name":"VM0003-IFM-Through-Extension-Of-Rotation-Age-v1.3.pdf"}}"""
    # cccev = extract_cccev(f"{DIR_INPUT}/{FILE_VM003}", iteration)
    # if len(cccev.requirements) > 0:
    #     CccevRepository(graph=GRAPH).save(cccev)
    #     disambiguate("DataUnit", iteration)
    #     disambiguate("InformationConcept", iteration)
    #     GraphEmbedder(embedder=EMBEDDER, graph=GRAPH).embed_graph()

    # reader = PdfReader(f"{DIR_INPUT}/{FILE_VM003}")
    # file_content = '\n'.join(map(lambda page: page.page_content, reader.load()))
    # trace = []
    # DocumentRepository(GRAPH).save(FILE_VM003, file_content, f"{DIR_INPUT}/{FILE_VM003}", {"iteration": iteration}, trace)
    # print(trace)
    # GraphEmbedder(embedder=EMBEDDER, graph=GRAPH).embed_graph()

    # vector = GRAPH.query("""
    #     MATCH (chunk:DocumentChunk)
    #     WITH chunk, rand() as r
    #     RETURN chunk.embedVector as vector
    #     ORDER BY r
    #     LIMIT 1
    # """)[0]["vector"]

    question = "What is the baseline scenario of this methodology?"
    # vector = EMBEDDER.embed_query(question)
    #
    # chunks = DocumentRepository(GRAPH).find_similar_chunks([f"{DIR_INPUT}/{FILE_VM003}"], vector, 5)
    #
    # answer = LLM.predict(f"""Answer the following question using the provided context. If you can't answer from the context, just say that you don't know.
    # After you answer the question, provide the raw text sources (not the identifiers).
    # Question: {question}
    # Context: {chunks}
    # """)


    # init_graph()
    # question = "What requirements must be met by a forest management project? Give me only short names"
    # question = "Detail the information I need to provide and their associated constraints"
    # question = "Give me the requirements that must be met, grouped by type of data"
    # question = "Which requirements use the same type of data as the Leakage Prevention Requirement?"
    # question = """Which requirements can I answer to with the following text? Every bit of information can be important and must be checked.
    # Text: This 3-year project does not use fire as part of its forest management.
    # """
    # question = """Find the questions of the information concept related to requirements on forest management projects, and find the answers in the following text.
    # Your final answer should contain every question that can be answered as a bullet list, along with their answer.
    # Text: This 3-year project does not use fire as part of its forest management.
    # """
    # question = """What requirements have been extracted from the document VM0003-IFM-Through-Extension-Of-Rotation-Age-v1.3.pdf?"""
    question = """What requirements have been extracted from the document VM0003?"""
    # question_graph(question)

    # html = convert_pdf(
    #     path=f"{DIR_INPUT}/{FILE_VM003}",
    #     format="html"
    # )
    #
    # WriteFileTool().run({
    #     "file_path": f"{DIR_OUTPUT}/vm003.html",
    #     "text": html
    # })
