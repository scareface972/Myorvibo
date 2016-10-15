# Myorvibo
Petit projet modeste permettant de commander un Orvibo Allone en python 3.4

## Requière
* Python python 3.4 ou plus fonctionne uniquement sous LINUX 

## Références
Ce projet permet d’utiliser la fonction IR du Orvibo Allone, il est basé sur le projet de Cherezov disponible à l’adresse : [git  Cherezov Orvibo](https://github.com/cherezov/orvibo) 

* Il utilise le Framework web Bottle pour un accès par requête http

* Il a été testé sur Raspberry pi et peut être amélioré à votre convenance 

## Utilisation

### Installer Bottle
``` shell
sudo pip3 install bottle
```
### Fonctionnement

#### Lancer main.py
telecharger Myorvibo,
``` shell
> cd myorvibo
> python3 main.py
```
#### Liste des commandes

* pour avoir la liste des orvibo allone ainsi que la liste des commandes ir enregistrées
exemple:
```http
http://ipraspberrypi:9000/api?action=discover
```
résultat: {ip :[ipOrvibo],commands :[[liste des commandes ir]]}

* pour lancer l'apprentissage d'une commande ir
exemple:

```http
http://ipraspberrypi:9000/api?action=learn&ip=iporvibo&touch=titre-de-la-touche
```
le <titre-de-la-touche> doit toujour etre de la forme suivante <touche.ir>.

* pour emettre une commande ir deux solutions
** soit une commande unique c'est a dire une seule touche:
exemple:
```http
http://ipraspberrypi:9000/api?action=learn&ip=iporvibo&touch=titre-de-la-touche
```
