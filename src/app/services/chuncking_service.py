def chunk_text(text: str, config:dict) -> list[str]:

    #text : le texte complet (page wiki)
    #size : taille maximale d’un chunk
    #overlap : chevauchement entre deux chunks
    # → le chevauchement évite de “couper une phrase ou une idée en deux

    size=config["chuncking"]["size"]
    overlap=config["chuncking"]["overlap"]


    chunks = []
    start = 0
    while start < len(text):
        c = text[start:start + size].strip() #strip() enlève les espaces / retours à la ligne au début et à la fin 
        if c:
            chunks.append(c)
        start += size - overlap
    return chunks