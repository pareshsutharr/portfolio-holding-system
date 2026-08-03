import pandas as pd

# =====================================
# KEYWORDS USED TO IDENTIFY HEADER ROW
# =====================================

HEADER_KEYWORDS = [

    "isin",
    "quantity",
    "qty",
    "stock name",
    "security name",
    "security",
    "company",
    "symbol",
    "buy value",
    "market value",
    "current value",
    "closing value",
    "average buy price",
    "unrealised p&l",
    "unrealized p&l"

]

# =====================================
# DETECT HEADER ROW
# =====================================

def detect_header(file_path):

    df = pd.read_excel(
        file_path,
        header=None
    )

    best_row = -1
    best_score = -1

    for index, row in df.iterrows():

        score = 0

        for cell in row:

            if pd.isna(cell):
                continue

            text = str(cell).strip().lower()

            for keyword in HEADER_KEYWORDS:

                if keyword in text:
                    score += 1

        if score > best_score:

            best_score = score
            best_row = index

    if best_row == -1:

        raise Exception(
            "Unable to detect header row."
        )

    headers = []

    for value in df.iloc[best_row]:

        if pd.isna(value):
            continue

        headers.append(
            str(value).strip()
        )

    print("\n========== HEADER DETECTION ==========\n")

    print(f"Header Row : {best_row}")
    print(f"Header Score : {best_score}")

    print("\nDetected Headers:\n")

    for header in headers:

        print(header)

    return {

        "dataframe": df,

        "header_row": best_row,

        "headers": headers

    }