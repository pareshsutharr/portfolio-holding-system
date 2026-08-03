# import pandas as pd
# import json
# from google import genai

# # =====================================
# # CONFIG
# # =====================================

# client = genai.Client(
#     api_key="AQ.Ab8RN6LWgVPbnuYZp49NZelhfb_A0oYnvslsd2EPmH2YK9GQlw"
# )

# file_path = "test_files/holdings.xlsx"

# # =====================================
# # READ EXCEL
# # =====================================

# df = pd.read_excel(
#     file_path,
#     header=None
# )

# # =====================================
# # FIND HEADER ROW
# # =====================================

# keywords = [
#     "isin",
#     "quantity",
#     "qty",
#     "stock name",
#     "security name",
#     "buy value",
#     "closing value",
#     "market value",
#     "average buy price",
#     "unrealised p&l"
# ]

# best_row_index = -1
# best_score = -1

# for index, row in df.iterrows():

#     score = 0

#     for cell in row:

#         if pd.isna(cell):
#             continue

#         cell_text = str(cell).strip().lower()

#         for keyword in keywords:
#             if keyword in cell_text:
#                 score += 1

#     if score > best_score:
#         best_score = score
#         best_row_index = index

# print(f"\nHeader Row Found: {best_row_index}")
# print(f"Header Score: {best_score}")

# # =====================================
# # EXTRACT HEADERS
# # =====================================

# headers = [
#     str(x).strip()
#     for x in df.iloc[best_row_index].tolist()
#     if pd.notna(x)
# ]

# print("\nDetected Headers:")
# print(headers)

# # =====================================
# # GEMINI PROMPT
# # =====================================

# prompt = f"""
# You are a portfolio statement expert.

# Map the following column headers to the standard fields below.

# Standard Fields:
# - security_name
# - isin
# - quantity

# Headers:
# {headers}

# Rules:
# 1. Return ONLY JSON.
# 2. If a field is not found return null.
# 3. No explanation.

# Example:

# {{
#     "security_name": "Stock Name",
#     "isin": "ISIN",
#     "quantity": "Quantity"
# }}
# """

# # =====================================
# # GEMINI CALL
# # =====================================

# response = client.models.generate_content(
#     model="gemini-2.5-flash",
#     contents=prompt
# )

# print("\nGemini Response:\n")
# print(response.text)

# # =====================================
# # CLEAN GEMINI RESPONSE
# # =====================================

# try:

#     clean_text = response.text.strip()

#     clean_text = clean_text.replace(
#         "```json",
#         ""
#     )

#     clean_text = clean_text.replace(
#         "```",
#         ""
#     )

#     clean_text = clean_text.strip()

#     mapping = json.loads(clean_text)

#     print("\nParsed Mapping:\n")
#     print(json.dumps(mapping, indent=4))

# except Exception as e:

#     print("\nJSON Parsing Failed")
#     print(e)

#     exit()

# # =====================================
# # CREATE HOLDINGS TABLE
# # =====================================

# holdings_df = df.iloc[
#     best_row_index + 1:
# ].copy()

# holdings_df.columns = headers

# holdings_df.reset_index(
#     drop=True,
#     inplace=True
# )

# # =====================================
# # CREATE STANDARD DATAFRAME
# # =====================================

# standard_df = pd.DataFrame()

# if mapping.get("security_name"):
#     standard_df["security_name"] = holdings_df[
#         mapping["security_name"]
#     ]

# if mapping.get("isin"):
#     standard_df["isin"] = holdings_df[
#         mapping["isin"]
#     ]

# if mapping.get("quantity"):
#     standard_df["quantity"] = holdings_df[
#         mapping["quantity"]
#     ]

# print("\n========== STANDARD DATAFRAME ==========\n")
# print(standard_df.to_string(index=False))