# whole-foods-deliverance
Making the Whole Foods delivery experience a little bit better

## Description
Born out of frustration with the perennially unavailable Whole Foods delivery slot, this is a simple script that uses an automated browser (Selenium) to navigate to your cart and refresh the delivery slot selection page until there is an opening.

When a slot is found, a friendly voice emanates from your speakers informing you of your good fortune.

Optionally, you can choose to be notified via SMS (Twilio) and/or Telegram by supplying API credentials in `conf.toml`.

More on these services here:
- [Twilio](https://www.twilio.com/docs/usage/tutorials/how-to-use-your-free-trial-account)
- [Telegram](https://core.telegram.org/bots#6-botfather)


## Requirements
- A mac (the audio alerts are mac-specific; the other bits may work on PC. YMMV)
- Python3.x (tested on 3.7) and Google Chrome (sorry)
- An Amazon Whole Foods cart populated with items
- Patience

## Installation
- Open the terminal
- Clone this repo (or download and unpack manually):
  ```
  git clone https://github.com/mark-thompson/whole-foods-deliverance.git
  ```
- Move to the cloned directory (if you downloaded manually, replace the `.` with the download location (e.g. `~/Downloads`)):
  ```
  cd ./whole-foods-deliverance
  ```
- Create and activate the environment:
  ```
  python3 -m venv env && . env/bin/activate
  ```
- Install the requirements:
  ```
  pip install -r requirements.txt
  ```
**Optional**
- Copy the config template to the default deployment location:
  ```
  cp conf_template.toml conf.toml
  ```
  Open the new file `conf.toml` with your favorite text editor and insert your API credentials

**Note:**
The default requirements assume you are using the current stable version of Chrome on mac (version 80).
If you are using a beta or dev release (version 81+) and you get an error when running the script, run
```
pip install --upgrade chromedriver-binary
```

## Usage
```
python run.py
```

On first run, you will be prompted to login. Subsequent runs will attempt to use a stored session cookie.
Run with the `-f` flag to force login and refresh the stored cookie.
```
python run.py -f
```
