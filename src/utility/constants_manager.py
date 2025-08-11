
from dotenv import load_dotenv, find_dotenv
import os

class ConstantsManager:
    _dotenv_loaded = False

    def __init__(self):
        if not ConstantsManager._dotenv_loaded:
            load_dotenv(dotenv_path=find_dotenv(), override=True)
            ConstantsManager._dotenv_loaded = True

    def get_variable(self, variableName):
        variable = os.environ.get(variableName, "")
        if variable == "":
            raise Exception(f"Could not find {variableName} environment variable")
        return variable
    
    def get_openai_organization_id(self):
        return self.get_variable('OPENAI_ORGANIZATION_ID')
    
    def get_openai_project_id(self):
        return self.get_variable('OPENAI_PROJECT_ID')
    
    def get_openai_api_key(self):
        return self.get_variable('OPENAI_API_KEY')
    
    def get_Mongodb_uri(self):
        return self.get_variable('MONGODB_URI')
    
    