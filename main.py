from seleniumbase import SB
from pathlib import Path
from seleniumbase.common.exceptions import NoSuchElementException as sb_NoSuchElementException, WebDriverException as sb_WebDriverException
from selenium.common.exceptions import NoSuchElementException , WebDriverException
import os
import re
import csv
from variables import oems, proxies
import time
import traceback
from datetime import datetime


class Parser():

	VARIABLE_FOR_CHANGE_SERVER = 550

	def __init__(self, not_first_setup=True, proxies=False, type_headless=True, oems=oems):
		
		self.type_headless = type_headless
		#check user data
		self.user_data = self.launch_user_data()
		self.not_first_setup = not_first_setup #берет полный лист без анализа csv
		
		self.oems = sorted(set(oems), key=oems.index)
		self.circle_proxy_list = []
		self.proxies = proxies
		if self.proxies:
			self.proxy = self.proxies.pop(0)
			print(f'использую {self.proxy}')
		else:
			self.proxy = proxies
			print(f'запустил без прокси')
		
		self.changes_of_proxy = 0
		self.main_process()
		
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

	def save_to_csv(self, row):
		with open('datas/emex.csv', 'a', newline='', encoding='utf-8') as f:
			writer = csv.writer(f, delimiter=';')
			writer.writerow(row)

	def get_last_oem_from_csv(self):
		with open('datas\\emex.csv', 'r', newline='', encoding='utf-8') as f:
			reader = f.readlines()[-1].split(';')
			last_oem = reader[1]
			return last_oem
	
	def change_proxy(self):
		self.changes_of_proxy += 1
		print(f'смена прокси номер {self.changes_of_proxy}')
		if self.request_counter > 0:
			self.circle_proxy_list.append(self.proxy)
		if self.proxies:
			self.proxy = self.proxies.pop(0)
			print(f'использую {self.proxy}')
		else:
			if self.circle_proxy_list:
				self.proxies = self.circle_proxy_list[:]
				self.circle_proxy_list = []
				self.proxy = self.proxies.pop(0)
				print(f'использую {self.proxy}')
			else:
				self.proxy = 'error'
				print('что-то прокси закончились')

	def refresh_list_oems(self):
		if self.not_first_setup:
			last_oem = self.get_last_oem_from_csv()
			if last_oem in self.oems:
				self.oems = self.oems[self.oems.index(last_oem)+1:]
		else:
			if self.changes_of_proxy != 0:
				self.not_first_setup = True
		print(f'Осталось пройти {len(self.oems)} оемов')


	def main_process(self):
		#initiliaze browser
		while self.oems:
			self.refresh_list_oems() #обновляю список нужных оемов
			self.request_counter = 0 #счетчик запросов
			with SB(user_data_dir=self.user_data, uc=True, proxy=self.proxy, page_load_strategy="eager", headless2=self.type_headless) as sb:
				self.driver = sb
				self.driver.set_window_position(0,0)
				self.driver.set_window_size(1430, 1100)
				#логика приложения вместо __name__=='__main__'
				for sku, main_oem in enumerate(self.oems):
					current_time = datetime.now().strftime("%H:%M:%S")
					print(f'{sku}, {main_oem}, {current_time}, запросов {self.request_counter}')
					if self.request_counter == 0 or self.request_counter % self.VARIABLE_FOR_CHANGE_SERVER != 0:
						check_to_change_proxy = self.first_page(sku, main_oem)
						if check_to_change_proxy:
							break
					else:
						print(f'сделал действий:{self.request_counter}')
						break
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
			print(f'сколько брендов в колбасе {number_of_requests}')
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
			self.driver.click_if_visible('xpath', f'//div[contains(@class, "brand-list")]//div[{i+1}][contains(@class, "row")]', timeout=10)

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
			self.driver.open(f'https://emex.ru/f?detailNum={main_oem}&packet=-1')
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
			row = [f'SKU{sku}', main_oem, 'таймаут', 'таймаут', 'таймаут', 'таймаут', self.proxy, current_time]
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
			row = [f'SKU{sku}', main_oem, 'нет в emex', 'нет в emex', 'нет в emex', 'нет в emex', self.proxy, current_time]
			self.save_to_csv(row) #создать функцию
		elif title == 'найдено несколько совпадений': #много брендов
			print('много брендов')
			try:
				brands, descriptions, analogs_descriptions_list, extra_oems = self.some_brands_func()
			except TypeError:
				return True
			if brands == []:
				row = [f'SKU{sku}', main_oem, 'нет в emex', 'нет в emex', 'нет в emex', 'нет в emex', self.proxy, current_time]
				self.save_to_csv(row) #создать функцию
			else:
				if extra_oems == []:
					extra_oems = ['нет доп оемов']
				row = [f'SKU{sku}', main_oem, ' // '.join(brands), ' // '.join(descriptions), ' // '.join(analogs_descriptions_list), ' // '.join(extra_oems), self.proxy, current_time]
				self.save_to_csv(row)
		else: #обычный оем
			print('обычный оем')
			try:
				main_brand, main_description, analog_descriptions_list, extra_oems = self.regular_oem_func(main_oem)
			except TypeError:
				print('обычный, но оказалось нет в emex')
				row = [f'SKU{sku}', main_oem, 'нет в emex', 'нет в emex', 'нет в emex', 'нет в emex', self.proxy, current_time]
				self.save_to_csv(row) #создать функцию
			except UnboundLocalError:
				print('что-то нет у него мейн бренда, видимо выдает другой оем')
				row = [f'SKU{sku}', main_oem, 'нет в emex', 'нет в emex', 'нет в emex', 'нет в emex', self.proxy, current_time]
				self.save_to_csv(row) #создать функцию
			else:
				# analogs_list = self.analog_oem_func() #функциональность аналогов (но долгое время работы)
				if extra_oems == []:
					extra_oems = ['нет доп оемов']
				row = [f'SKU{sku}', main_oem, main_brand, main_description, ' // '.join(analog_descriptions_list), ', '.join(extra_oems), self.proxy, current_time]
				self.save_to_csv(row)
		
		return None
if __name__ == '__main__':

	test = Parser(not_first_setup=True, proxies=proxies, type_headless=False)