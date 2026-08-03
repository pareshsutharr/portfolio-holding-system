from config import HOLDINGS_FILE
from header_detection import detect_header

result = detect_header(HOLDINGS_FILE)

print(result["header_row"])
print(result["headers"])