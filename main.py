from seleniumbase import SB, BaseCase
from pathlib import Path
from seleniumbase.common.exceptions import NoSuchElementException as sb_NoSuchElementException, WebDriverException as sb_WebDriverException, TextNotVisibleException as sb_TextNotVisibleException
from selenium.common.exceptions import NoSuchElementException , WebDriverException
import os
import re
import csv
from variables import oems, proxies
import time
import traceback
from datetime import datetime


class Parser():

	VARIABLE_FOR_CHANGE_SERVER = 495

	def __init__(self, not_first_setup=True, type_input=False, proxies=False, type_headless=True, type_user_data=False, oems=oems):
		
		#блок иницилизации
		self.not_first_setup = not_first_setup #берет полный лист без анализа csv
		self.input = type_input
		self.type_headless = type_headless
		self.oems = sorted(set(oems), key=oems.index) #формирую лист оемов без дубликатов

		self.browser_location = 'C:\\Program Files\\Google\\Chrome Beta\\Application\\chrome.exe'
		
		#юзер дата
		self.user_data = False
		if type_user_data:
			self.user_data = self.launch_user_data()
		
		#прокси блок
		self.circle_proxy_list = []
		self.proxies = proxies
		if self.proxies:
			self.proxy = self.proxies.pop(0)
			print(f'использую {self.proxy}')
		else:
			self.proxy = proxies
			print(f'запустил без прокси')
		
		#все счетчики
		self.saved_in_session = 0
		self.changes_of_proxy = 0
		self.errors_in_a_row = 0
		self.all_requests = 0
		
		while self.oems or self.errors_in_a_row > 10:
			try:
				self.main_process()
				self.errors_in_a_row = 0
			except Exception as e:
				if self.proxy == 'error':
					print('что-то прокси закончилось')
					print(f'self proxies{self.proxies}')
					print(f'self circle proxies list{self.circle_proxy_list}')
					break
				current_time = datetime.now().strftime("%H:%M:%S")
				e = traceback.format_exc().replace('\n', '&N&').replace('\t', '&TAB&')
				error = f'{type(e)} + {e}'
				row = [f'sku{self.saved_in_session}', self.oem, error, 'ошибка', '-', '-', self.proxy, f'смен {self.changes_of_proxy}', f'локально зап: {self.request_counter}', f'всего зап: {self.all_requests}', current_time]
				self.save_to_csv(row)
				self.errors_in_a_row += 1


		
	@staticmethod
	def benchmark(func):

		def wrapper(*args, **kwargs):
			start = time.time()
			result = func(*args, **kwargs)
			end = time.time()
			print('[*] Время выполнения: {} секунд.'.format(end-start))
			return result
		return wrapper

	@staticmethod
	def delete_wrong_symbols(oem): #Функция убирает пробелы в оеме
		oem = re.sub(r'[^A-Z\d]', r'', oem.upper())
		return oem
	
	@staticmethod
	def change_quotes(obj):
		obj = obj.replace('"', "'")
		return obj
	
	@staticmethod
	def launch_user_data():
		user_data = f"{Path().absolute()}/chrome_profile/"
		if not os.path.isdir(user_data):
			os.mkdir(user_data)
		Path(f'{user_data}First Run').touch()
		return user_data

	def save_to_csv(self, row, delimiter=';;'):
		with open('datas/emex.csv', 'a', newline='', encoding='utf-8') as f:
			f.write(delimiter.join(row)+'\n')
			self.saved_in_session += 1


	def get_last_oem_from_csv(self, delimiter=';;'):
		with open('datas\\emex.csv', 'r', newline='', encoding='utf-8') as f:
			try:
				reader = f.read().splitlines()
				last_oem = reader[-1].split(delimiter)[1]
				return last_oem
			except IndexError:
				print('csv файл пуст')
				return None

	def change_proxy(self):
		self.changes_of_proxy += 1
		print(f'смена прокси номер {self.changes_of_proxy}')
		self.circle_proxy_list.append(self.proxy)
		if self.proxies:
			self.proxy = self.proxies.pop(0)
			print(f'использую {self.proxy}')
		else:
			if self.circle_proxy_list:
				self.proxies = self.circle_proxy_list[:]
				self.circle_proxy_list = []
				self.proxy = self.proxies.pop(0)
				print(f'использую {self.proxy}, смена прокси номер {self.changes_of_proxy}')
			else:
				self.proxy = 'error'

	def refresh_list_oems(self):
		if self.not_first_setup:
			last_oem = self.get_last_oem_from_csv()
			if last_oem in self.oems:
				self.oems = self.oems[self.oems.index(last_oem)+1:]
		else:
			if self.changes_of_proxy != 0:
				self.not_first_setup = True
		print(f'Осталось пройти {len(self.oems)} оемов')

	def version_checker(self):
		siteversion = self.driver.get_cookie("siteversion")
		location = self.driver.get_cookie("best-location")
		switcher = self.driver.get_cookie("new-site-switcher")
		timeout = 0
		while siteversion == None and timeout < 30:
			siteversion = self.driver.get_cookie("siteversion")
			location = self.driver.get_cookie("best-location")
			switcher = self.driver.get_cookie("new-site-switcher")
			timeout += 1

		if siteversion["value"] != "1":
			self.driver.delete_all_cookies()
			self.driver.load_cookies(name="cookies.txt")
			self.driver.refresh()
			self.request_counter += 1
			self.all_requests += 1

	def main_process(self):
		#initiliaze browser
		while self.oems:
			
			self.refresh_list_oems() #обновляю список нужных оемов
			self.request_counter = 0 #счетчик запросов
			with SB(user_data_dir=self.user_data, uc=True, proxy=self.proxy, page_load_strategy="normal", headless2=self.type_headless) as sb:
				if self.input:
					x = input('Введите Enter для начала:')
				self.driver = sb
				self.driver.set_window_position(0,0)
				self.driver.set_window_size(1430, 1100)
				#логика приложения вместо __name__=='__main__'
				for sku, self.oem in enumerate(self.oems):
					current_time = datetime.now().strftime("%H:%M:%S")
					print(f'{self.saved_in_session}, {self.oem}, {current_time}, запросов {self.request_counter}, всего {self.all_requests}')
					if self.request_counter == 0 or self.request_counter % self.VARIABLE_FOR_CHANGE_SERVER != 0:
						check_to_change_proxy = self.first_page(sku, self.oem)
						if check_to_change_proxy:
							break
					else:
						break
			print(f'пора менять прокси, сделал действий:{self.request_counter}')
			self.change_proxy()
		
	def some_brands_func(self):
		
		brands = []
		descriptions = []
		extra_oems = []
		analogs_descriptions_list = []

		def collect_info(oem_variable, brands=brands, descriptions=descriptions, extra_oems=extra_oems):
			nonlocal analogs_descriptions_list
			if oem_variable == '':
				self.request_counter += 1
				self.all_requests += 1
				return
			try:
				brand, description, analog_descriptions_list, final_extra_oems_list = self.regular_oem_func(oem_variable)
			except TypeError:
				return None
			if analog_descriptions_list != []:
				analogs_descriptions_list = analogs_descriptions_list[:] + analog_descriptions_list[:]

			brands.append(brand)
			description_row = brand + ' && ' + description
			descriptions.append(description_row)
			if final_extra_oems_list != []:
				extra_oem = brand + ' && ' + ', '.join(final_extra_oems_list)
				extra_oems.append(extra_oem)
		
		request_prediction = len(self.driver.find_elements('xpath', '//div[contains(@class, "brand-list")]//div[contains(@class, "row")]'))
		if self.request_counter+request_prediction > self.VARIABLE_FOR_CHANGE_SERVER:
			return None
		
		oem_variable = self.driver.get_text('xpath', '//div[contains(@class, "brand-list")]//div[1][contains(@class, "row")]//span[contains(@class, "link-like")]') #беру значение номера
		
		self.driver.click_if_visible('xpath', '//div[contains(@class, "brand-list")]//div[1][contains(@class, "row")]')#переход в первый бренд
		
		collect_info(oem_variable)
		
		self.driver.click_if_visible('//span[contains(@data-bind, "click: emex.find.brandList.showBrandsDialog")]', 'xpath', timeout=10)

		number_of_requests = len(self.driver.find_elements('xpath', '//div[contains(@class, "brand-list")]//div[contains(@class, "row")]//span[contains(@class, "link-like")]'))
		
		if number_of_requests:
			pass
		else:
			print('ничего не взяло из len_brands_row(мб не успело)')
		
		for i in range(1, number_of_requests):
			if i % 2:
				self.driver.sleep(1)
			else:
				self.driver.sleep(3)

			oem_variable = self.driver.get_text('xpath', f'//div[contains(@class, "brand-list")]//div[{i+1}][contains(@class, "row")]//span[contains(@class, "link-like")]', timeout=10)
			if oem_variable == '':
				continue
			
			self.driver.js_click(f'div.brand-list > div:nth-child({i+1})')

			try:
				self.driver.wait_for_element_present('//span[contains(@data-bind, "click: emex.find.brandList.showBrandsDialog")]', 'xpath', timeout=10)
			except sb_NoSuchElementException:

				if self.driver.is_element_visible('xpath', '//div[contains(@class, "error-container")]'):
					return None
				else:
					print('что-то элемент не загрузился, но и ошибки нет')
					raise Exception
			except Exception:
				print('почему-то попал сюда вообще не знаю почему')
			else:
				collect_info(oem_variable)
				
				if i != number_of_requests-1:
					self.driver.click_if_visible('//span[contains(@data-bind, "click: emex.find.brandList.showBrandsDialog")]', 'xpath', timeout=10)

		return sorted(brands), sorted(descriptions), sorted(set(analogs_descriptions_list)), sorted(extra_oems)
			
	
	def regular_oem_func(self, main_oem):
		
		self.request_counter += 1
		self.all_requests += 1
		if self.driver.is_element_visible('xpath', '//div[contains(@class, "error-container")]'):
			return None
		try:
			self.driver.wait_for_element_present('xpath', "//div[contains(@class, 'original-list')]//div[contains(@class, 'expandable-list')]", timeout=10)
		except sb_NoSuchElementException:
			return None
		oem_blocks = self.driver.find_elements('xpath', "//div[contains(@class, 'original-list')]//div[contains(@class, 'expandable-list')]")
		
		brand_oem_list = [] #результаты поиска по оригинальному бренду мейн оема
		analogs_description_list = []
		extra_oems_list = []
		final_extra_oems_list = []
		main_oem_clear = self.delete_wrong_symbols(main_oem)
		for oem_block in oem_blocks:

			brand = oem_block.find_element('xpath', './/span[contains(@class, "detail-make")]').text
			if '"' in brand:
				brand = self.change_quotes(brand)
			oem = self.delete_wrong_symbols(oem_block.find_element('xpath', ".//div[contains(@class, 'detail-numbers')]/div[contains(@data-bind,'linkOrText: { text: detailInfo.VisibleNum, href: emex.find.brand.replacementSearchlUrl(detailInfo) }')]").text)

			description = oem_block.find_element('xpath', './/div[contains(@class, "one-string")]').text
			if description:
				if '"' in description:
					description = self.change_quotes(description)
				analogs_description_list.append(description)

			try:
				extra_oem = self.delete_wrong_symbols(oem_block.find_element('xpath', ".//div[contains(@class, 'replace-number')]").text)
			except NoSuchElementException:
				extra_oem = None

			if main_oem_clear == oem:
				main_brand = brand
				main_description = description
				extra_oems_list.append(main_oem_clear)
				if extra_oem:
					extra_oems_list.append(extra_oem)	

			oem_block_dict = {
				"oem":oem,
				"extra_oem":extra_oem,
			}
			brand_oem_list.append(oem_block_dict)
		
		while extra_oems_list:
			checked_extra_oem = extra_oems_list.pop(0)
			if main_oem_clear != checked_extra_oem:
				final_extra_oems_list.append(checked_extra_oem)
			for oem_block_dict in brand_oem_list:
				sub_oem = oem_block_dict["oem"]
				sub_extra_oem = oem_block_dict["extra_oem"]

				if (checked_extra_oem == sub_oem) and (sub_extra_oem != None) and (sub_extra_oem not in extra_oems_list) and (sub_extra_oem not in final_extra_oems_list):
					extra_oems_list.append(sub_extra_oem)
				if (checked_extra_oem == sub_extra_oem) and (sub_oem not in extra_oems_list) and (sub_oem not in final_extra_oems_list):
					extra_oems_list.append(sub_oem)

		return main_brand, main_description, sorted(set(analogs_description_list)), sorted(final_extra_oems_list)
	
	@benchmark
	def analog_oem_func(self):
		
		analogs_list = []
		self.driver.wait_for_element_present('xpath', "//div[contains(@data-bind, 'visible: sections.AnalogDetails.isVisible')]//div[contains(@class, 'make-group expandable-list')]", timeout=10)
		analog_blocks = self.driver.find_elements('xpath', "//div[contains(@data-bind, 'visible: sections.AnalogDetails.isVisible')]//div[contains(@class, 'make-group expandable-list')]")
		for analog_block in analog_blocks:
			analog_brand = analog_block.find_element('xpath', './/span[contains(@class, "detail-make")]').text.strip()
			analog_number = analog_block.find_element('xpath', './/div[contains(@data-bind, "linkOrText: { text: detailInfo.VisibleNum, href: emex.find.brand.replacementSearchlUrl(detailInfo) }")]').text.strip()
			analog_description = analog_block.find_element('xpath', './/div[contains(@class, "one-string")]').text.strip()
			row_result = analog_brand + ' && ' + analog_number + ' && ' + analog_description
			analogs_list.append(row_result)
		return sorted(analogs_list)
	
	def first_page(self, sku, main_oem):
		
		#вызов первой страницы
		try:
			self.driver.driver.default_get(f'https://emex.ru/f?detailNum={main_oem}&packet=-1')
			if sku == 0:
				seconds_counter = 0
				while 'emex.ru' not in self.driver.get_current_url() and seconds_counter < 60:
					print(f'ВОШЕЛ В WHILE {seconds_counter/5+1} раз')
					self.driver.sleep(5)
					self.driver.driver.default_get(f'https://emex.ru/f?detailNum={main_oem}&packet=-1')
					url_error = self.driver.get_current_url()
					current_time = datetime.now().strftime("%H_%M_%S") 
					self.driver.save_screenshot(f'errors\\js_error{seconds_counter/5+1}_{url_error}_{current_time}.png')
					self.driver.sleep(5)
					seconds_counter += 5
				self.version_checker()
		except WebDriverException:
			print(f'что-то страница не загружатеся, вот номер запроса {self.request_counter}')
			return True
		if sku % 2 == 0:
			self.driver.sleep(1)
		else:
			self.driver.sleep(3)


		title = self.driver.get_title().lower()
		timeout_timer = 0
		while title == 'результаты поиска' and timeout_timer != 30:
			if self.driver.is_element_visible('xpath', '//div[contains(@class, "error-container")]'):
				title = 'превышена частота обновлений'
			else:
				self.driver.sleep(1)
				title = self.driver.get_title().lower()
				timeout_timer += 1
		
		current_time = datetime.now().strftime("%H:%M:%S")
		if title == 'результаты поиска': #таймаут
			print('таймаут')
			self.request_counter += 1
			self.all_requests += 1
			row = [f'SKU{self.saved_in_session}', main_oem, 'таймаут', 'таймаут', 'таймаут', 'таймаут', self.proxy, f'смен {self.changes_of_proxy}', f'смен {self.changes_of_proxy}', f'локально зап: {self.request_counter}', f'всего зап: {self.all_requests}', current_time]
			self.save_to_csv(row) #создать функцию
		elif self.driver.is_element_visible('xpath', '//span[@jsselect="heading"]'): #дохлый прокси, не грузит страницу вообще
			#title = 'emex.ru'
			print('менять прокси')
			return True
		elif title == 'превышена частота обновлений':
			print('превышена частота обновлений')
			print('менять прокси')
			return True
		elif self.driver.is_element_visible("div[class='no-results'][style='']"): #нет в emex
			print('нет в emex')
			self.request_counter += 1
			self.all_requests += 1
			row = [f'SKU{self.saved_in_session}', main_oem, 'нет в emex', 'нет в emex', 'нет в emex', 'нет в emex', self.proxy, f'смен {self.changes_of_proxy}', f'локально зап: {self.request_counter}', f'всего зап: {self.all_requests}', current_time]
			self.save_to_csv(row) #создать функцию
		elif title == 'найдено несколько совпадений': #много брендов
			print('много брендов')
			try:
				brands, descriptions, analogs_descriptions_list, extra_oems = self.some_brands_func()
			except TypeError:
				return True
			if brands == []:
				row = [f'SKU{self.saved_in_session}', main_oem, 'нет в emex', 'нет в emex', 'нет в emex', 'нет в emex', self.proxy, f'смен {self.changes_of_proxy}', f'локально зап: {self.request_counter}', f'всего зап: {self.all_requests}', current_time]
				self.save_to_csv(row) #создать функцию
			else:
				if extra_oems == []:
					extra_oems = ['нет доп оемов']
				row = [f'SKU{self.saved_in_session}', main_oem, ' // '.join(brands), ' // '.join(descriptions), ' // '.join(analogs_descriptions_list), ' // '.join(extra_oems), self.proxy, f'смен {self.changes_of_proxy}', f'локально зап: {self.request_counter}', f'всего зап: {self.all_requests}', current_time]
				self.save_to_csv(row)
		else: #обычный оем
			print('обычный оем')
			try:
				main_brand, main_description, analog_descriptions_list, extra_oems = self.regular_oem_func(main_oem)
			except TypeError:
				print('обычный, но оказалось нет в emex')
				row = [f'SKU{self.saved_in_session}', main_oem, 'нет в emex', 'нет в emex', 'нет в emex', 'нет в emex', self.proxy, f'смен {self.changes_of_proxy}', f'локально зап: {self.request_counter}', f'всего зап: {self.all_requests}', current_time]
				self.save_to_csv(row) #создать функцию
			except UnboundLocalError:
				print('что-то нет у него мейн бренда, видимо выдает другой оем')
				self.driver.save_screenshot(f'errors\\no_brand_error{main_oem}.png')
				row = [f'SKU{self.saved_in_session}', main_oem, 'нет в emex', 'нет в emex', 'нет в emex', 'нет в emex', self.proxy, f'смен {self.changes_of_proxy}', f'локально зап: {self.request_counter}', f'всего зап: {self.all_requests}', current_time]
				self.save_to_csv(row) #создать функцию
			else:
				# analogs_list = self.analog_oem_func() #функциональность аналогов (но долгое время работы)
				if extra_oems == []:
					extra_oems = ['нет доп оемов']
				row = [f'SKU{self.saved_in_session}', main_oem, main_brand, main_description, ' // '.join(analog_descriptions_list), ', '.join(extra_oems), self.proxy, f'смен {self.changes_of_proxy}', f'локально зап: {self.request_counter}', f'всего зап: {self.all_requests}', current_time]
				self.save_to_csv(row)
		return None
	
if __name__ == '__main__':
	test = Parser(not_first_setup=True, type_input=False, proxies=proxies, type_headless=True)