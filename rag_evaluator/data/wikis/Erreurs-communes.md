[[_TOC_]]

# Erreurs rencontrées
- "NU1301 Unable to load the service index for source" : voir la résolution des erreurs d'accès, ci-dessous.
- "NU1900 Error occurred while getting package vulnerability data" : voir la résolution des erreurs d'accès, ci-dessous.

# Résolution

## Erreurs d'accès
En cas d'erreur d'accès, vérifier le PAT stocké dans le fichier `NuGet.config` présent dans le dépôt (à la racine ou près de la solution).

Il s'agit de la valeur de la clé `ClearTextPassword`. Elle est générée par le compte `<SERVICE_ACCOUNT>` (demander à l'équipe responsable).

```XML
  <packageSourceCredentials>
    <INTERNAL_PACKAGE_SOURCE>
      <add key="Username" value="<SERVICE_ACCOUNT>" />
      <add key="ClearTextPassword" value="${NUGET_PAT}" />
      <add key="ValidAuthenticationTypes" value="basic" />
    </INTERNAL_PACKAGE_SOURCE>
  </packageSourceCredentials>
```
