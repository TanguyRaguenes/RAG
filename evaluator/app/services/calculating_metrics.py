import math
from typing import List


# Rappel format du dataset :
#{
    #"question": "Quelle est la différence d'usage entre Kelio et Moffi ?",
    #"keywords": ["Kelio", "Moffi", "badgeage", "réservation"],
    #"reference_answer": "Kelio gère le badgeage et les absences. Moffi sert à la réservation de postes de travail en présentiel.",
    #"category": "tools_usage"
#}

#_____________________________________________________________________________________________________________________

# MRR (Mean Reciprocal Rank)
# On regarde la position du tout premier chunk pertinent. Puis on calule l'inverse.
# rappel : L'inverse d'une fraction consiste à échanger le numérateur (le chiffre du haut) et le dénominateur (le chiffre du bas) 
# tout en conservant le même signe. Mathématiquement, si nous avons une fraction "a/b", son inverse est "b/a".
#
# Exemple :
# Si le bon chunk est en 1ère position : score = 1/1 = 1.0
# Si le bon chunk est en 2ème position : score = 1/2 = 0.5
# Si le bon chunk est en 10ème position : score = 1/10 = 0.1
# Pas de chunk pertinent ? Score = 0.
def calculate_mrr(keywords: List[str], retrieved_chunks: List[str]) -> float:

    if not keywords or not retrieved_chunks:
        return 0.0

    keywords_lower = [keyword.lower() for keyword in keywords]
    retrieved_chunks_lower = [chunk.lower() for chunk in retrieved_chunks]

    rr_scores = []
    
    for keyword in keywords_lower:

        found = False 
        
        # On cherche le mot dans les chunks
        for rank, text in enumerate(retrieved_chunks_lower, start=1):
            if keyword in text.lower():
                rr_scores.append(1.0 / rank)
                found = True
                break
        
        if not found:
            rr_scores.append(0.0)

    # Calcul de la moyenne (Mean)
    if not rr_scores:
        return 0.0
    return sum(rr_scores) / len(rr_scores)

#_____________________________________________________________________________________________________________________

# nDCG (Normalized Discounted Cumulative Gain)
# On vérifie si les meilleurs chunks sont bien placés tout en haut de la liste.
# On compare le score du classement du retriever avec le score d'un classement "Idéal" (parfait).
# rappel : Le logarithme (log2) sert ici d'amortisseur. Contrairement à une division simple qui tue le score trop vite 
# (diviser par 2 fait perdre 50%), le log réduit le score plus doucement à mesure qu'on descend dans la liste (pour plus de détails voir plus bas).
# C'est une "punition" progressive pour les bons chunks mal classés.
#
# Exemple (Question : "Différence Kelio/Moffi") :
# - Chunk A (Parfait) et Chunk B (Moyen) sont pertinents. Chunk C (Inutile) est du bruit.
# - Classement [A, B, C] (Idéal) : Le meilleur est en 1er -> Score = 1.0 (100%)
# - Classement [B, A, C] (Moyen) : Le meilleur est tombé en 2ème -> Score < 1.0 (ex: 0.85)
# - Classement [C, B, A] (Mauvais): Les bons chunks sont à la fin -> Score très faible.

def calculate_ndcg(keywords: List[str], retrieved_chunks: List[str], k: int) -> float:

    if not keywords or not retrieved_chunks:
        return 0.0

    keywords_lower = [keyword.lower() for keyword in keywords]
    retrieved_chunks_lower = [chunk.lower() for chunk in retrieved_chunks]

    # Pour chaque chunk, on dit qu'il vaut 1 (pertinent) si :
    # N'IMPORTE LEQUEL (any) des mots-clés est présent dans ce texte.
    relevances = []

    for chunk in retrieved_chunks_lower[:k]:

        # Est-ce que au moins un des mots-clés est dans ce texte ?
        is_relevant = any(keyword in chunk for keyword in keywords_lower)
        
        if is_relevant:
            relevances.append(1)
        else:
            relevances.append(0)

    # 1. Score réel
    actual_dcg = calculate_dcg(relevances)
    
    # 2. Score idéal (On trie les 1 d'abord)
    # sorted : Trie la liste.
    # reverse=True : Du plus grand au plus petit (Descendant).
    idcg = calculate_dcg(sorted(relevances, reverse=True))
    
    return (actual_dcg / idcg) if idcg > 0 else 0.0

def calculate_dcg(relevances: List[int]) -> float:

    dcg = 0.0
    # On parcourt toute la liste de relevances fournie
    for i, rel in enumerate(relevances):
        # Rappel : i commence à 0, donc on divise par log2(i + 2)
        # math.log2 parce que diviser par le rang (1, 2, 3...) tue le score trop vite. 
        # Le logarithme est un amortisseur (plus proche de la logique humaine) qui dit : "C'est moins bien d'être 2ème, mais c'est quand même bien."
        # log2(X) = Combien de fois dois-je multiplier 2 par lui-même pour arriver à X ?
        # log2(2) = 1 (Car 2^1 = 2) -> Il faut un seul 2. 
        # log2(4) = 2 (Car 2 * 2 = 4) -> Il faut deux 2.
        # log2(8) = 3 (Car 2 * 2 * 2 = 8) -> Il faut trois 2.
        # Donc 1/2 = 0.5 soit 50% alors que 1/log2(3)=0.63 soit 63%
        dcg += rel / math.log2(i + 2)
    return dcg

#_____________________________________________________________________________________________________________________

# Recall@K (Rappel - Couverture de Mots-clés)
# On regarde si on a trouvé TOUS les mots-clés demandés par l'utilisateur.
# On divise le nombre de mots trouvés par le nombre total de mots-clés cherchés.
# rappel : Dans un contexte académique, le Rappel mesure le % de documents trouvés par rapport à la base totale.
# Ici, faute de connaitre la base par cœur, on utilise une approximation : "ai-je trouvé tous les mots-clefs ?".
#
# Exemple (Keywords cherchés : "Kelio", "Moffi", "Badgeage") :
# - Si les chunks contiennent "Kelio" et "Moffi" mais pas "Badgeage" :
# - Trouvés = 2. Total attendu = 3.
# - Score = 2/3 = 0.66 (66% de couverture).

def calculate_recall(keywords: List[str], retrieved_chunks: List[str]) -> float:

    if not keywords or not retrieved_chunks:
        return 0.0
    
    keywords_lower = [keyword.lower() for keyword in keywords]
    retrieved_chunks_lower = [chunk.lower() for chunk in retrieved_chunks]

    found_count = 0

    for keyword in keywords_lower:
        
        # La fonction any() renvoie True dès qu'elle trouve le mot dans un des textes.
        # Elle s'arrête immédiatement quand elle a trouvé (pas besoin de tout lire).
        if any(keyword in chunk for chunk in retrieved_chunks_lower):
            found_count += 1

    return found_count / len(keywords)

#_____________________________________________________________________________________________________________________

# Precision@K (Précision)
# On regarde la "pureté" de la liste des chunks: y a-t-il des déchets (chunks inutiles) parmi les chunks affichés ?
# On divise le nombre de chunks pertinents par le nombre de chunks affichés (K).
# rappel : L'ordre n'a aucune importance ici. Que le déchet soit en 1ère ou en 3ème position, 
# il compte de la même façon comme une erreur de précision.
#
# Exemple (Question : "Frais Cleemy", on affiche 3 chunks) :
# - Chunk 1 : Pertinent (Parle de Cleemy)
# - Chunk 2 : Bruit (Menu Cantine)
# - Chunk 3 : Pertinent (Parle de Frais)
# - Score : 2 pertinents sur 3 affichés = 2/3 = 0.66 (66%).

def calculate_precision(keywords: List[str], retrieved_chunks: List[str], k) -> float:

    if not keywords or not retrieved_chunks:
        return 0.0

    keywords_lower = [keyword.lower() for keyword in keywords]
    retrieved_chunks_lower = [text.lower() for text in retrieved_chunks]

    considered_chunks = retrieved_chunks_lower[:k]
    relevant_chunks_count = 0
    
    if not considered_chunks:
        return 0.0
    
    # On parcourt les chunks UN PAR UN.
    # Un chunk est pertinent s'il contient AU MOINS UN mot-clé.
    # On évite ainsi de compter un chunk plusieurs fois.
    for chunk in considered_chunks:
        is_relevant = any(kw in chunk for kw in keywords_lower)
        if is_relevant:
            relevant_chunks_count += 1
            
    return relevant_chunks_count / len(considered_chunks)