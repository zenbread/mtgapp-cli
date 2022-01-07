# Setup
Install python3, pip env should come with it.
Create virtual environment
Install requirements
Use app

## Dependencies
- Python3
- Python3 -m venv <name_you_choose>

## With git
git clone https://github.com/zenbread/mtgapp.git
## Without git 
https://github.com/zenbread/mtgapp
click clone at top and get the zip
extract the zip

## Install
```
cd mtgapp
python -m venv venv (or other name)
```
Windows:
```
venv\scripts\activate.ps1 or .bat if in cmd (why are you in cmd?)
```
Linux:
```
source venv/bin/activate OR
. venv/bin/activate
```
Requirements:
```
pip install -r requirements.txt
```
## Running
`python mtgapp.py`


## Accounts
In shell: <br>
create new user (Option 1) <br>
type command: <br>
`update` # Wait for download to finish

# Use:
### Add cards
Use tcgplayer app to scan cards. On the app you can press the three dots, ..., to export to csv. Export and move to computer. Place in directory of the mtgapp.

`shell::>add csv <filename>`

Will load cards and then update the list.

### Search
You can search for cards by typing in the names (only names right now) and you can look for cards on your copy/paste clipboard. <br>
`shell::> search name:<card name> or any other text comparison's from MTG Arena` OR <br>
`shell::> search clip` <br>
Format for clip:
```
2 Card name to search
1 Smothering Tithe
```
### Cards in Hand
You can add cards into your hand as it asks you to clarify choices. This is for removing inventory and other features later.
You can look at cards in hand: <br>
`shell::> cih print` OR `shell::> cih`


