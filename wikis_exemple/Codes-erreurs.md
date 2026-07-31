[[_TOC_]]

Ce document liste les code d'erreur géré par Isilog lors de l'encapsulation.

#IsiSmtp
- **ILM-0001 :** Une erreur inattendue est survenue lors du traitement de connexion au SMTP.
  - Consulter les traces avancées pour voir le message retourné par l'erreur.
- **ILM-0002 :** Une erreur est survenue lors de la connexion au SMTP.
  - Vérifier l'adresse du serveur SMTP et le port.
- **ILM-0003 :** Une erreur est survenue lors de l'authentification auprès du SMTP.
  - Vérifier les informations de connexions.
- **ILM-0004 :** Une erreur inattendue est survenu lors de l'envoi du mail.
  - Vérifier que toutes les informations du mails sont valides.
- **ILM-0020 :** Erreur lors de l'envoi de mail.
  - Vérifier l'authentification anonyme.

#IsiPop
- **ILM-0005 :** Une erreur inattendue est survenue lors du traitement de connexion au POP.
  - Consulter les traces avancées pour voir le message retourné par l'erreur.
- **ILM-0006 :** Une erreur est survenue lors de la connexion au POP.
  - Vérifier l'adresse du serveur POP et le port.
- **ILM-0007 :** Une erreur est survenue lors de l'authentification auprès du POP.
  - Vérifier les informations de connexions.
- **ILM-0008 :** Une erreur est survenue lors de la récupération de la liste de message.
  - Consulter les traces avancées pour voir le message retourné par l'erreur.
- **ILM-0009 :** Une erreur est survenue lors la récupération d'un message.
  - Consulter les traces avancées pour voir le message retourné par l'erreur.
- **ILM-0010 :** Une erreur est survenue lors la sauvegarde des pièces jointes d'un message.
  - Consulter les traces avancées pour voir le message retourné par l'erreur.
- **ILM-0019 :** Une erreur est survenue lors de la sauvegarde des médias liés au mail.
  - Consulter les traces avancées pour voir le message retourné par l'erreur.

#IsiImap
- **ILM-0011 :** Une erreur inattendue est survenue lors du traitement de connexion au IMAP.
  - Consulter les traces avancées pour voir le message retourné par l'erreur.
- **ILM-0012 :** Une erreur est survenue lors de la connexion IMAP.
  - Vérifier l'adresse du serveur et le port.
- **ILM-0013 :** Une erreur est survenue lors de l'authentification auprès d'IMAP.
  - Vérifier les informations de connexion.
- **ILM-0014 :** Une erreur est survenue lors de la récupération de la liste de message.
  - Consulter les traces avancées pour voir le message retourné par l'erreur.
- **ILM-0015 :** Une erreur est survenue lors la récupération d'un message.
  - Consulter les traces avancées pour voir le message retourné par l'erreur.
- **ILM-0016 :** Une erreur est survenue lors de la sauvegarde des pièces jointes d'un message.
  - Consulter les traces avancées pour voir le message retourné par l'erreur.
- **ILM-0017 :** Vous tentez de récupérer des mails alors que vous n'êtes pas authentifié.
  - Vérifier la connexion avant de consulter les mails.
- **ILM-0018 :** Une erreur est survenue lors de la sauvegarde des médias liés au mail.
  - Consulter les traces avancées pour voir le message retourné par l'erreur.


#IsiMicrosoftOAuthProvider
- **ILM-0021 :** Une erreur est survenue lors de la création du provider Microsoft Graph
  - Vérifier les informations de connexion
- **ILM-0022 :** Une erreur s'est produite lors de l'enregistrement des pièces jointes
  - Consulter les traces avancées pour voir le message retourné par l'erreur.
- **ILM-0023 :** Une erreur s'est produite lors de l'enregistrement de l'email
  - Consulter les traces avancées pour voir le message retourné par l'erreur.
- **ILM-0024 :** "Une erreur s'est produite lors de la suppression de l'email
  - Consulter les traces avancées pour voir le message retourné par l'erreur.
- **ILM-0025 :** Les pièces jointes n'ont pas été enregistrées car le chemin d'enregistrement n'a pas été spécifié
  - Vérifier le chemin d'enregistrement des pièces-jointes
- **ILM-0026 :** Les médias n'ont pas été enregistrés car le chemin d'enregistrement n'a pas été spécifié
  - Vérifier le chemin d'enregistrement des médias
- **ILM-0027 :** Une erreur s'est produite lors de l'envoi d'un email
  - Consulter les traces avancées pour voir le message retourné par l'erreur.
- **ILM-0028 :** Une erreur s'est produite lors de la création de l'événement calendrier
  - Consulter les traces avancées pour voir le message retourné par l'erreur.
- **ILM-0029 :** Une erreur s'est produite lors de la récupération de l'email
  - Consulter les traces avancées pour voir le message retourné par l'erreur.
- **ILM-0030 :** Une erreur s'est produite lors de la récupération des pièces-jointes liés à un email
  - Consulter les traces avancées pour voir le message retourné par l'erreur.
- **ILM-0031 :** Une erreur s'est produite lors de la récupération de la pièce jointe
  - Consulter les traces avancées pour voir le message retourné par l'erreur.
- **ILM-0032 :** Une erreur est survenue lors de l'ajout d'une pièce-jointe dans le message
  - Consulter les traces avancées pour voir le message retourné par l'erreur.
- **ILM-0033 :** Une erreur lors de la modification de l'état de lecture du mail
  - Consulter les traces avancées pour voir le message retourné par l'erreur.