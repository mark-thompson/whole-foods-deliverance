# whole-foods-deliverance
Enhancing the Whole Foods / Amazon Fresh delivery experience.

### Features:
 - Slot Availability Notifications (audio / [SMS / Telegram](#optional))
 - [Auto checkout](#checkout)
 - [Slot preferences](#optional)
 - [OOS alert bypass](#ignore-oos)
 - [Cart tracking](#save-cart)

## Description
Born out of frustration with the perennially unavailable Whole Foods / Amazon Fresh delivery slot, this is a simple script that uses an automated browser (Selenium) to navigate to your cart and refresh the delivery slot selection page until there is an opening.
When a slot is found, a friendly voice emanates from your speakers informing you of your good fortune.

If called with the `--checkout` flag, the program will also attempt to select a slot for you and checkout automatically.

Optionally, you can choose to be notified via SMS (Twilio) and/or Telegram by supplying API credentials in `conf.toml`.

More on these services here:
- [Twilio](https://www.twilio.com/docs/usage/tutorials/how-to-use-your-free-trial-account)
- [Telegram](https://core.telegram.org/bots#6-botfather)


## Requirements
- A computer (audio alerts have been tested on Mac and Windows)
- Python3.x (tested on 3.7) and Google Chrome (sorry)
- A Whole Foods or Amazon Fresh cart populated with items
- Patience

## Installation
- Open Terminal (or Powershell if on Windows)
- Clone this repo, or download and unpack manually (see [this](https://help.github.com/en/github/creating-cloning-and-archiving-repositories/cloning-a-repository) for help):
  ```
  git clone https://github.com/mark-thompson/whole-foods-deliverance.git
  ```
- Move to the cloned directory (if you downloaded manually, replace the `.` with the download location
  (e.g. `~/Downloads`, `C:\Users\{username}\Downloads`)):
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

#### Optional
*Do this if you want to send SMS/Telegram notifications or specify delivery slot preferences*

- Copy the [config template](https://github.com/mark-thompson/whole-foods-deliverance/blob/master/conf_template.toml) to the default deployment location:
  ```
  cp conf_template.toml conf.toml
  ```
- Open the new file `conf.toml` with your favorite text editor and insert your API credentials

#### Note
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
Run the script with the default options:
```
python run.py
```
Or specify one or more options to change the script behavior. e.g.:
```
python run.py -s 'Amazon Fresh' --checkout --ignore-oos --debug
```

### Options


#### Service
Specify the delivery service you are using with the `-s` or `--service` option. Quotes are required.

_Defaults to:_ `'Whole Foods'`
```
python run.py -s 'Amazon Fresh'
```

#### Checkout
Use the `-c` or `--checkout` flag to attempt to checkout automatically when a slot is found. Uses your delivery window preferences as specified in `conf.toml` under the `slot_preference` key. _See: [config template](https://github.com/mark-thompson/whole-foods-deliverance/blob/master/conf_template.toml)_
```
python run.py --checkout
```

#### Ignore-OOS
At some point, you may encounter an out of stock alert. By default, the program will produce an audio alert and give you some time to continue through the alert prompt if you've decided the item in question isn't essential to your order.

Use the `--ignore-oos` flag if you'd like to bypass these alerts automatically.
*Details of the removed items will be saved to a local file: `removed_items_{timestamp}.toml`*
```
python run.py --ignore-oos
```

#### Save-Cart
Occasionally (and rather unhelpfully), items will disappear from your cart without generating any kind of alert.
Use the `--save-cart` flag to write a local file containing all of your cart items before the slot search begins.
```
python run.py --save-cart
```

#### Debug
Among other things, the `--debug` flag will save the current page source if a Selenium error is encountered. Use this if you are getting an error and want to help contribute to a fix
```
python run.py --debug
```
---

*Inspiration credit: [this much more interestingly named project](https://github.com/johntitus/bungholio)*
