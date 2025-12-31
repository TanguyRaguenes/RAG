from langchain_text_splitters import RecursiveCharacterTextSplitter

def chunk_text(text: str, config: dict) -> list[str]:

    size = config["chuncking"]["size"]
    overlap = config["chuncking"]["overlap"]

    text = text.replace("[[_TOC_]]", "").strip()

    # Initialisation du splitter LangChain
    # Il va essayer de couper dans l'ordre : \n\n, \n, " ", ""
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=size,
        chunk_overlap=overlap,
        length_function=len,
        is_separator_regex=False,
    )

    # Découpage effectif
    chunks = text_splitter.split_text(text)
    
    return chunks