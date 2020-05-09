import toml
import config
from gooey import Gooey, GooeyParser
from run import run
import sys

time_slots = [
    "Any",
    "5:00 AM - 7:00 AM",
    "7:00 AM - 9:00 AM",
    "9:00 AM - 11:00 AM",
    "11:00 AM - 1:00 PM",
    "1:00 PM - 3:00 PM",
    "3:00 PM - 5:00 PM",
    "5:00 PM - 7:00 PM",
    "7:00 PM - 9:00 PM",
    "9:00 PM - 11:00 PM" 
    ]

# update config based on values selected by user
def update_config(args, c):
    #make sure config has all the necessary keys
    for o in ["options","slot_preference"]:
        if not c.get(o):
            c.update({o:{}})
    # now update options
    if args.any_day:
        c["slot_preference"].update({"Any":args.any_day})
    else:
        c["slot_preference"].update({"Any":[]})
    if args.today:
        c["slot_preference"].update({"today":args.today})
    else:
        c["slot_preference"].update({"today":[]})
    if args.tomorrow:
        c["slot_preference"].update({"tomorrow":args.tomorrow})
    else:
        c["slot_preference"].update({"tomorrow":[]})
    if args.card:
        c["options"].update({"preferred_card":args.card})
    else:
        c["options"].update({"preferred_card":""})
    if args.use_smile:
        c["options"].update({"use_smile":args.use_smile})
    else:
        c["options"].update({"use_smile":False})
    if args.chrome_data_dir:
        c["options"].update({"chrome_data_dir":args.chrome_data_dir})
    else:
        c["options"].update({"chrome_data_dir":""})
    if args.checkout:
        c["options"].update({"checkout":args.checkout})
    else:
        c["options"].update({"checkout":False})
    if args.ignore_oos:
        c["options"].update({"ignore_oos":args.ignore_oos})
    else:
        c["options"].update({"ignore_oos":False})
    if args.save_cart:
        c["options"].update({"save_cart":args.save_cart})
    else:
        c["options"].update({"save_cart":False})
    if args.no_import:
        c["options"].update({"no_import":args.no_import})
    else:
        c["options"].update({"no_import":False})
    #and save file
    with open(config.CONF_PATH, 'w') as conf_file:
        toml.dump(c,conf_file)

@Gooey
def run_gui():
    c = toml.load(config.CONF_PATH)
    card_num = c.get('options',{}).get("preferred_card","")
    smile = c.get('options',{}).get("use_smile",False)
    any_day = c.get('slot_preference',{}).get("Any",[])
    today = c.get('slot_preference',{}).get("Today",[])
    tomorrow = c.get('slot_preference',{}).get("Tomorrow",[])
    chrome_data_dir = c.get('options',{}).get("chrome_data_dir","")
    checkout = c.get('options',{}).get("checkout","")
    ignore_oos = c.get('options',{}).get("ignore_oos","")
    save_cart = c.get('options',{}).get("save_cart","")
    no_import = c.get('options',{}).get("no_import","")    

    parser = GooeyParser(description="Amazon ordering helper")
    parser.add_argument('--service', '-s', choices=config.VALID_SERVICES,
                        default=config.VALID_SERVICES[0],
                        help="The Amazon delivery service to use")
    parser.add_argument('--any_day', help="Delivery preferences for any day", 
                        widget="Listbox", nargs='+', choices=time_slots, default=any_day)
    parser.add_argument('--today', help="Delivery preferences for today", 
                        widget="Listbox", nargs='+', choices=time_slots, default=today)
    parser.add_argument('--tomorrow', help="Delivery preferences for tomorrow", 
                        widget="Listbox", nargs='+', choices=time_slots, default=tomorrow)
    parser.add_argument('--card', action='store', default=card_num,
                        help="Last 4 digits of credit card to use")
    parser.add_argument('--use_smile', action='store_true', default=smile,
                        help="Use Amazon Smile for checkout")
    parser.add_argument('--checkout', '-c', action='store_true', default=checkout,
                        help="Select first available slot and checkout")
    parser.add_argument('--ignore-oos', action='store_true', default=ignore_oos,
                        help="Ignores out of stock alerts, but attempts to "
                             "save removed item details to a local TOML file")
    parser.add_argument('--save-cart', action='store_true', default=save_cart,
                        help="Saves your cart information to a local TOML file")
    parser.add_argument('--no-import', action='store_true', default=no_import,
                        help="Don't import chromedriver_binary. Set this flag "
                             "if using an existing chromedriver in $PATH")
    parser.add_argument('--chrome_data_dir', default=chrome_data_dir, widget='DirChooser',
                        help="Path of an existing Chrome profile")
    parser.add_argument('--debug', action='store_true')
    
    args = parser.parse_args()
    update_config(args, c)
    try:
        run(args)
    except Exception:
        sys.exit("Something went wrong")

if __name__ == '__main__':
    run_gui()
