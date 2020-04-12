# whole-foods-deliverance
Enhancing the Whole Foods / Amazon Fresh delivery experience with availability notifications, auto-checkout, and slot preferences

## Description
Born out of frustration with the perennially unavailable Whole Foods / Amazon Fresh delivery slot, this is a simple script that uses an automated browser (Selenium) to navigate to your cart and refresh the delivery slot selection page until there is an opening.
When a slot is found, a friendly voice emanates from your speakers informing you of your good fortune.

If called with the `--checkout` flag, the program will also attempt to select a slot for you and checkout automatically.

Optionally, you can choose to be notified via SMS (Twilio) and/or Telegram by supplying API credentials in `conf.toml`.

More on these services here:
- [Twilio](https://www.twilio.com/docs/usage/tutorials/how-to-use-your-free-trial-account)
- [Telegram](https://core.telegram.org/bots#6-botfather)


## Requirements
- A computer (the audio alerts are Mac-specific; all other functionality works on Windows)
- Python3.x (tested on 3.7) and Google Chrome (sorry)
- A Whole Foods or Amazon Fresh cart populated with items
- Patience

## Installation
- Open Terminal (or Powershell if on Windows)
- Clone this repo (or download and unpack manually):
  ```
  git clone https://github.com/mark-thompson/whole-foods-deliverance.git
  ```
- Move to the cloned directory (if you downloaded manually, replace the `.` with the download location (e.g. `~/Downloads`)):
  ```
  cd ./whole-foods-deliverance
  ```
- Create the python virtual environment:
  ```
  python3 -m venv env
  ```
- Activate the environment *(you'll need to do this again for every new terminal session)*:
  - Mac:
    ```
    . env/bin/activate
    ```
  - Windows:
    ```
    . env/Scripts/activate
    ```
- Install the requirements *(you only need to do this once)*:
  ```
  pip install -r requirements.txt
  ```
**Optional:** *(Do this if you want to send SMS/Telegram notifications or specify delivery slot preferences)*
- Copy the config template to the default deployment location:
  ```
  cp conf_template.toml conf.toml
  ```
  Open the new file `conf.toml` with your favorite text editor and insert your API credentials

**Note:**
The default requirements assume you are using the current stable version of Chrome (version 81).
If you are using a beta or dev release (version 82+) and you get an error when running the script, run:
```
pip install --upgrade chromedriver-binary
```

If you are still using Chrome version 80, run:
```
pip install --upgrade chromedriver-binary==80.0.3987.106.0
```

## Usage
```
python run.py
```

### Options

Use one or more of the following options to change the script behavior.
_e.g.:_ `python run.py -s 'Amazon Fresh' -c --debug`

*Service*
Specify the service you are using with the `-s` or `--service` option. Quotes are required.
_Defaults to `'Whole Foods'`_
```
python run.py -s 'Amazon Fresh'
```

*Auto Checkout*
Run with the `-c` or `--checkout` flag to attempt to checkout when a slot is found. Uses your delivery window preferences as specified in `conf.toml` under the `slot_preference` key.
_(See `conf_template.toml`)_
```
python run.py -c
```

*Force Login*
On first run, you will be prompted to login. Subsequent runs will attempt to use locally stored session data.
If you find you are prompted to login frequently, run the script with the `-f` or `--force_login` flag to force login and refresh the stored data:
```
python run.py -f
```

*Debug*
Among other things, the `--debug` flag will save the current page source if a Selenium error is encountered. Use this if you are getting an error and want to help contribute to a fix
```
python run.py --debug
```
---

*Inspiration credit: [this much more interestingly named project](https://github.com/johntitus/bungholio)*
