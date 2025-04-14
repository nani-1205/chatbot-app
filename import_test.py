import sys
import importlib

print("Python sys.path:")
for p in sys.path:
    print(p)

try:
    from langchain_community.chat_models import ChatGoogleGenerativeAI
    print("\nSuccessfully imported ChatGoogleGenerativeAI from langchain_community.chat_models")
    print(f"Module langchain_community.chat_models.__file__: {langchain_community.chat_models.__file__}") # Print module file path

except ImportError as e:
    print(f"\nImportError: {e}")

try:
    langchain_community_spec = importlib.util.find_spec("langchain_community.chat_models")
    if langchain_community_spec:
        print(f"\nlangchain_community.chat_models spec found: {langchain_community_spec}")
    else:
        print("\nlangchain_community.chat_models spec NOT found")
except ModuleNotFoundError:
     print("\nModuleNotFoundError for langchain_community.chat_models during spec check")