from database.models import init_collections
import sys
import os

# Ensure the backend directory is on sys.path so that
# `database` resolves as a package regardless of where the
# script is launched from.
sys.path.insert(0, os.path.dirname(__file__))

collections = init_collections()


print(collections)
