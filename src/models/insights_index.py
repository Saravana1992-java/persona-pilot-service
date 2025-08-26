from src.models.insights_mappings import insights_mappings
from src.models.insights_settings import insights_settings

insights_index = {
    "settings": insights_settings["settings"],
    "mappings": insights_mappings
}
