# Myorvibo
Petit projet modeste permettant de commander un Orvibo Allone en python 3.4.

## Requière

* Python python 3.4 ou plus.

* Il utilise le Framework web Bottle pour un accès par requête http.

* Il a été testé sur Raspberry pi et peut être amélioré à votre convenance. 

## Références
Ce projet permet d’utiliser la fonction IR du Orvibo Allone, il est basé sur le projet de Cherezov disponible à l’adresse : [git  Cherezov Orvibo](https://github.com/cherezov/orvibo).
D’autres fonctions verront le jour par la suite.

## Utilisation

### Installer Bottle
``` shell
sudo pip3 install bottle
```
### Fonctionnement

#### Lancer main.py
Télécharger Myorvibo,
``` shell
> cd myorvibo
> python3 main.py
```
#### Liste des commandes

* Pour avoir la liste des orvibo allone ainsi que la liste des commandes IR enregistrées.
Exemple:
```http
http://ipraspberrypi:9000/api?action=discover
```
Résultat: {ip :[ipOrvibo],commands :[[liste des commandes IR]]}

* Pour lancer l'apprentissage d'une commande IR
Exemple:

```http
http://ipraspberrypi:9000/api?action=learn&ip=iporvibo&touch=tv_1.ir
```
Résultat: {"cmd": "commande envoyées", "succes": true} ou en cas d'échec {"cmd": "commande envoyées", "succes": false}

Le titre de la touche doit toujours être de la forme suivante <touche.ir> (éviter les symboles +/-;) . L'adresse IP de l'orvibo est facultative si vous n'avez qu'un orvibo, mais l'exécution de la commande sera beaucoup plus lente.

Pour émettre une commande IR deux solutions
- Soit une seule touche:

Exemple:
```http
http://ipraspberrypi:9000/api?action=send&ip=iporvibo&touch=tv_1.ir
```
Résultat: {"cmd": "commande émise", "succes": true} ou en cas d'échec {"cmd": "commande émise", "succes": false}

- Soit une liste de commandes du type [tv_2.ir,tv_1.ir] autant que vous le souhaitez mais toujours séparé par <,> et se terminant toutes par <.ir>

Exemple:
```http
http://ipraspberrypi:9000/api?action=send&ip=iporvibo&touch=tv_2.ir,tv_1.ir
```
Résultat: {"cmd": "liste de commandes émises", "succes": true} ou en cas d'échec {"cmd": "liste des commandes émises", "succes": false}

