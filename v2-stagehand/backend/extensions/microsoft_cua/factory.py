from enum import Enum

from stagehand import AgentProvider
from stagehand.agent.agent import MODEL_TO_CLIENT_CLASS_MAP, MODEL_TO_PROVIDER_MAP
from .microsoft_cua import MicrosoftCUAClient
import logging

logger = logging.getLogger(__name__)


all_providers = {member.name: member.value for member in AgentProvider}
all_providers['MICROSOFT'] = 'microsoft'

ExtendedAgentProvider = Enum('ExtendedAgentProvider', all_providers, type=str)

def register_microsoft_cua():

    MODEL_TO_CLIENT_CLASS_MAP["microsoft-fara-7b"] = MicrosoftCUAClient
    MODEL_TO_CLIENT_CLASS_MAP["microsoft/fara-7b"] = MicrosoftCUAClient
    MODEL_TO_CLIENT_CLASS_MAP["microsoft/Fara-7B"] = MicrosoftCUAClient
    MODEL_TO_PROVIDER_MAP["microsoft-fara-7b"] = ExtendedAgentProvider.MICROSOFT
    MODEL_TO_PROVIDER_MAP["microsoft-fara-7b"] = ExtendedAgentProvider.MICROSOFT
    MODEL_TO_PROVIDER_MAP["microsoft/Fara-7B"] = ExtendedAgentProvider.MICROSOFT

    logger.info("Registered microsoft cua model")

def create_stagehand_with_microsoft_cua(stagehand_instance):

    register_microsoft_cua()

    return stagehand_instance