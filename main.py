import seleniumbase as sb
from pathlib import Path
import os

class Parser():

	oems_dict = {
		'FD3046': 'много брендов',
		'VN031108': 'нет в emex',
		'452060K010': 'Toyota'
	}

	oem = 'VN031108'

	def __init__(self, proxy=False):
		
		#check user data
		user_data = f"{Path().absolute()}/chrome_profile/"
		if not os.path.isdir(user_data):
			os.mkdir(user_data)
		Path(f'{user_data}First Run').touch()
		
		if proxy:
			self.proxies = proxy
		
		
		#initiliaze browser
		self.driver = sb.Driver(user_data_dir=user_data, uc=True, proxy=proxy)
		self.driver.maximize_window()

	def first_page(self, oem):
		
		#вызов первой страницы
		self.driver.open(f'https://emex.ru/f?detailNum={oem}&packet=-1')

		title = self.driver.get_title().lower()
		timeout_timer = 0
		while title == 'результаты поиска' or timeout_timer == 30:
			self.driver.sleep(1)
			title = self.driver.get_title().lower()
			timeout_timer += 1

		if title == 'результаты поиска':
			print('таймаут') #создать функцию
		elif title == 'поиск по номеру детали':
			print('нет в emex') #создать функцию
		elif title == 'найдено несколько совпадений':
			print('много брендов') #создать функцию
		else:
			print('обычный оем') #создать функцию




if __name__ == '__main__':
	test = Parser()
	for oem in ('FD3046', 'VN031108', '452060K010'):
		test.first_page(oem)