# obd2

Application Python KivyMD pour lire de vraies donnees OBD2 depuis un adaptateur compatible ELM327.

## Installation

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## Partage du projet

Pour recuperer le projet sur un autre PC et lancer directement le mode test avec faux DTC :

```bash
git clone https://github.com/Hibaaguir/obd2.git
cd obd2
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
powershell -ExecutionPolicy Bypass -File .\run_app_with_fake_dtc.ps1
```

Dans ce mode :

- `run_app_with_fake_dtc.ps1` demarre l'emulateur fake DTC ;
- l'emulateur ecoute sur `127.0.0.1:35000` ;
- puis l'application se lance et peut s'y connecter.

## Notes

- L'application n'integre pas de mode simulation.
- Un adaptateur OBD2 reel ou un emulateur TCP doit etre accessible.
- La connexion OBD actuelle utilise TCP/IP.
- La configuration OBD par defaut est centralisee dans `app/core/obd_config.py`.
- Les donnees affichees sont centralisees dans `app/core/elm_pid_registry.py`.
- Le dashboard interroge directement l'ELM327 en commandes brutes pour supporter les PID standards et les PID custom Toyota de `ELM327-emulator`.

## Configuration OBD

La configuration actuelle est adaptee a `ELM327-emulator` en TCP/IP :

```python
OBD_HOST = "127.0.0.1"
OBD_PORT = 35000
OBD_BAUDRATE = 38400
OBD_TIMEOUT = 10
```

Dans cette configuration :

- `ELM327-emulator` ecoute sur `127.0.0.1:35000`
- l'application se connecte a cette adresse TCP
- `OBD_BAUDRATE` est passe a `python-obd` uniquement pour eviter son auto-detection de debit, qui envoie `\x7F\x7F` et perturbe `ELM327-emulator`

Pour passer plus tard a un vrai adaptateur ELM327 Bluetooth, garde le changement isole dans `app/core/obd_config.py` et dans `app/services/obd_service.py`, qui centralise la creation de la connexion.

Tester la connexion OBD depuis le terminal :

```bash
python test_obd.py
```

## Test sans voiture

L'application ne contient aucun mode simulation interne. Pour tester sans voiture, utilise un outil externe comme `ELM327-emulator`, qui expose un faux adaptateur ELM327 via TCP. L'application continue alors a se connecter comme si elle parlait a un adaptateur ELM327 classique.

Installer l'emulateur :

```bash
python -m pip install ELM327-emulator
```

Lance l'emulateur en mode TCP :

```bash
elm -s car -n 35000
```

Ensuite, lance l'application ou le script `test_obd.py`. Par defaut, ils utilisent `127.0.0.1` et le port `35000`.

Dans l'application, va sur l'ecran Accueil pour verifier ou modifier l'adresse IP et le port TCP.

Pour lancer automatiquement l'emulateur DTC de test puis l'application :

```powershell
powershell -ExecutionPolicy Bypass -File .\run_app_with_fake_dtc.ps1
```

Ce lanceur ouvre l'emulateur de faux DTC (`P0301`, `P0420`), attend que le port TCP `35000` soit pret, puis demarre l'application.

Important : dans tous les cas, la simulation est fournie par `ELM327-emulator`, pas par le code de l'application.

## Donnees exploitees par l'application

Le dashboard affiche uniquement les PID connus dans `app/core/elm_pid_registry.py`.
Si l'emulateur repond `NO DATA` ou `?`, la carte reste visible mais indique que la donnee n'est pas supportee.

Les donnees principales sont :

- moteur : RPM, vitesse, temperature moteur, charge moteur, pression admission, temperature admission, debit MAF, position papillon, tension ECU ;
- hybride : SOC batterie HV, courant batterie HV, temperatures MG1/MG2, couples MG1/MG2 ;
- vehicule : odometre, carburant, VIN, temperature ambiante.

Les mesures sont sauvegardees dans SQLite avec les valeurs decodees et un champ JSON `raw_data`, utile pour une future couche d'analyse ou d'intelligence artificielle.

## Build Android avec Buildozer

Le fichier `buildozer.spec` prepare le packaging Android avec les dependances suivantes :

- `kivy`
- `kivymd`
- `obd`
- `pyserial`

Il declare aussi les permissions Android utiles pour un usage OBD2 avec reseau ou Bluetooth :

- `INTERNET`
- `ACCESS_NETWORK_STATE`
- `BLUETOOTH`
- `BLUETOOTH_ADMIN`
- `BLUETOOTH_SCAN`
- `BLUETOOTH_CONNECT`
- `ACCESS_FINE_LOCATION`

Les permissions Bluetooth recentes sont necessaires sur Android 12+ pour scanner ou communiquer avec des peripheriques Bluetooth. Android peut aussi demander l'autorisation "Nearby devices" au lancement selon la version du systeme.

### Preparation sous WSL/Linux

Installe les outils systeme :

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git zip unzip openjdk-17-jdk autoconf libtool pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo6 cmake libffi-dev libssl-dev
```

Cree un environnement Python pour Buildozer :

```bash
python3 -m venv .venv-buildozer
source .venv-buildozer/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install buildozer cython
```

Genere l'APK debug :

```bash
buildozer android debug
```

L'APK sera genere dans le dossier `bin/`.

Installer l'APK sur un telephone branche en USB avec le mode developpeur actif :

```bash
buildozer android deploy
```

Lancer l'application et afficher les logs :

```bash
buildozer android debug deploy run logcat
```

Pour repartir d'un build propre :

```bash
buildozer android clean
buildozer android debug
```

Note importante : ce build ne rajoute aucun mode simulation dans l'application. Pour tester sans voiture, utilise la section "Test sans voiture" avec un emulateur externe.
