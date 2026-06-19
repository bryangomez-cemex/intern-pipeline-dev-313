import os
import struct
import pyodbc
from dotenv import load_dotenv
from azure.identity import InteractiveBrowserCredential

print("Starting SQL connection test with Microsoft Entra token...")

load_dotenv()

server = os.getenv("AZURE_SQL_SERVER")
database = os.getenv("AZURE_SQL_DATABASE")

print("Server:", server)
print("Database:", database)

if not server:
    raise ValueError("AZURE_SQL_SERVER is missing from .env")

if not database:
    raise ValueError("AZURE_SQL_DATABASE is missing from .env")

credential = InteractiveBrowserCredential()
token = credential.get_token("https://database.windows.net/.default").token

token_bytes = token.encode("utf-16-le")
token_struct = struct.pack(f"<I{len(token_bytes)}s", len(token_bytes), token_bytes)

SQL_COPT_SS_ACCESS_TOKEN = 1256

connection_string = (
    "DRIVER={ODBC Driver 18 for SQL Server};"
    f"SERVER=tcp:{server},1433;"
    f"DATABASE={database};"
    "Encrypt=yes;"
    "TrustServerCertificate=no;"
    "Connection Timeout=60;"
)

print("Attempting connection...")

conn = pyodbc.connect(
    connection_string,
    attrs_before={SQL_COPT_SS_ACCESS_TOKEN: token_struct}
)

cursor = conn.cursor()
cursor.execute("SELECT 1")
print("SQL connection works:", cursor.fetchone()[0])

cursor.close()
conn.close()
print("Done.")