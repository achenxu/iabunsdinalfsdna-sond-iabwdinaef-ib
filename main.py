import requests
from bs4 import BeautifulSoup as bs
from random import *
from time import sleep
import string
import _thread
from flask import Flask, render_template, request, redirect
from datetime import datetime
import logging
import json
import webbrowser

from utils import n_logging, c_logging


tokens = []

def captureToken(token):
	expiry = datetime.now().timestamp() + 115
	tokenDict = {
		'expiry': expiry,
		'token': token
	}
	tokens.append(tokenDict)
	return

def sendToken():
	while not tokens:
		pass
	token = tokens.pop(0)
	return token['token']

def manageTokens():
	while True:
		for item in tokens:
			if item['expiry'] < datetime.now().timestamp():
				tokens.remove(item)
		sleep(5)

app = Flask(__name__)

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

@app.route('/', methods=['GET'])
def base():
	return redirect("http://germanconnec.adidas.de:5000/solve", code=302)

@app.route('/solve', methods=['GET'])
def solve():
	sitekey = "6LdyFRkUAAAAAF2YmQ9baZ6ytpVnbVSAymVpTXKi"
	return render_template('index.html', sitekey=sitekey)


@app.route('/submit', methods=['POST'])
def submit():
	token = request.form.get('g-recaptcha-response', '')
	captureToken(token)
	return redirect("http://germanconnec.adidas.de:5000/solve", code=302)


class Generator():

	def __init__(self, locale, sitekey, pageurl):
		self.locale = locale.upper()
		if locale.upper() == "DE":
			self.domain = '.de'
			self.language = 'de_DE'
		else:
			self.domain = '.com'
			self.language = 'en_US'
		self.sitekey = sitekey
		self.pageurl = pageurl
		self.delay = 2

	def __get_captcha_id(self):
		params = {
			'googlekey': self.sitekey,
			'pageurl': self.pageurl,
			'method': 'userrecaptcha',
			'key': self.apikey
		}
		r = requests.post('http://2captcha.com/in.php', params=params)
		captcha_id = r.text.split('|')[1]
		return captcha_id

	def __get_captcha_token(self, captcha_id):
		params = {
			'id': captcha_id,
			'action': 'get',
			'key': self.apikey
		}
		r = requests.get('http://2captcha.com/res.php', params=params)
		while 'CAPCHA_NOT_READY' in r.text:
			sleep(self.delay)
			r = requests.get('http://2captcha.com/res.php', params=params)
		captcha_token = r.text.split('|')[1]
		return captcha_token

	def fetch_token(self):
		captcha_id = self.__get_captcha_id()
		captcha_token = self.__get_captcha_token(captcha_id)
		return captcha_token

	def create_account(self, email, password, captcha_token):		
		headers = {
			'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.98 Safari/537.36',
			'Accept-Encoding': 'gzip, deflate, sdch, br',
			'Accept-Language': 'en-GB,en;q=0.8',
			'Upgrade-Insecure-Requests': '1'
		}
		s = requests.Session()
		s.headers.update(headers)
		r = s.get('https://cp.adidas{}/web/eCom/{}/loadcreateaccount'.format(self.domain, self.language))
		csrftoken = bs(r.text, "html.parser").find('input', {'name': 'CSRFToken'})['value']
		s.headers.update({
			'Origin': 'https://cp.adidas{}'.format(self.domain),
			'Referer': 'https://cp.adidas{}/web/eCom/{}/loadcreateaccount'.format(self.domain, self.language)
			})
		data = {
			'firstName': 'German',
			'lastName': 'Connec',
			'minAgeCheck': 'true',
			'day': '12',
			'month': '09',
			'year': '1998',
			'_minAgeCheck': 'on',
			'email': email,
			'password': password,
			'confirmPassword': password,
			'_amf': 'on',
			'terms': 'true',
			'_terms': 'on',
			'metaAttrs[pageLoadedEarlier]': 'true',
			'app': 'eCom',
			'locale': self.language,
			'domain': '',
			'consentData1': 'Sign me up for adidas emails, featuring exclGBive offers, featuring latest product info, news about upcoming events, and more. See our <a target="_blank" href="https://www.adidas.co.uk/GB/help-topics-privacy_policy.html">Policy Policy</a> for details.',
			'consentData2': '',
			'consentData3': '',
			'CSRFToken': csrftoken,
			'g-recaptcha-response': captcha_token
			}
		r = s.post('https://cp.adidas{}/web/eCom/{}/accountcreate'.format(self.domain, self.language), data=data)
		account = '{}:{}'.format(email, password)
		if r.status_code == requests.codes.ok:
			return True, account
		else:
			return False, None



if __name__ == '__main__':
	with open('config.json') as file:
		config = json.load(file)
		file.close()
	_thread.start_new_thread(app.run, ())
	_thread.start_new_thread(manageTokens, ())
	accountsList = []
	n_logging("Adidas Account Creator v1.0.0")
	n_logging("GermanConnec")
	n_logging("***************************************************************************")
	creator = Generator(config['locale'], '6LdyFRkUAAAAAF2YmQ9baZ6ytpVnbVSAymVpTXKi', 'https://www.adidas.com')
	num = input("# ACCOUNTS: ")
	webbrowser.open('http://germanconnec.adidas.de:5000/solve')
	n_logging("Started account generator.")
	for x in range(int(num)):
		email = '{}-{}@{}'.format(config['prefix'], randint(1111,999999999), config['domain'])
		allchar = string.ascii_letters + string.digits
		passw = "".join(choice(allchar) for x in range(randint(8, 12)))
		n_logging("Task {} - Waiting for captcha token.".format(x))
		# token = creator.fetch_token()
		token = sendToken()
		n_logging("Task {} - Obtained captcha token.".format(x))
		result, account = creator.create_account(email, passw, token)
		if result:
			n_logging("Task {} - Created account {}".format(x, account))
			accountsList.append(account)
		else:
			n_logging("Task {} - Failed to create account.".format(x))
	with open('accounts.txt', 'w') as file:
		for item in accountsList:
			file.write('{}\n'.format(item))
		file.close()
	n_logging("Saved accounts to txt file.")
