from seleniumbase import SB
from pathlib import Path
from selenium.common.exceptions import NoSuchElementException
import os
import re
import csv
from variables import oems
import time

class Parser():

	def __init__(self, proxy=False):
		
		#check user data
		user_data = f"{Path().absolute()}/chrome_profile/"
		if not os.path.isdir(user_data):
			os.mkdir(user_data)
		Path(f'{user_data}First Run').touch()
		
		if proxy:
			self.proxies = proxy
		
		#initiliaze browser
		with SB(user_data_dir=user_data, uc=True, proxy=proxy, page_load_strategy="eager") as sb:
			self.driver = sb
			self.driver.set_window_position(300,1153)
			self.driver.maximize_window()
			#логика приложения вместо __name__=='__main__'
			for sku, main_oem in enumerate(oems):
				self.first_page(sku, main_oem)
	
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
	
	def save_to_csv(self, row):
		with open('datas/emex.csv', 'a', newline='', encoding='utf-8') as f:
			writer = csv.writer(f, delimiter=';')
			writer.writerow(row)

	def some_brands_func(self, main_oem):
		
		brands = []
		descriptions = []
		extra_oems = []
		analogs_descriptions_list = []

		def collect_info(brands=brands, descriptions=descriptions, extra_oems=extra_oems):
			nonlocal analogs_descriptions_list
			brand, description, analog_descriptions_list, final_extra_oems_list = self.regular_oem_func(main_oem)
			if analog_descriptions_list != []:
				analogs_descriptions_list = analogs_descriptions_list[:] + analog_descriptions_list[:]
			brands.append(brand)
			description_row = brand + ' && ' + description
			descriptions.append(description_row)
			if final_extra_oems_list != []:
				extra_oem = brand + ' && ' + ', '.join(final_extra_oems_list)
				extra_oems.append(extra_oem)
		
		self.driver.find_element('xpath', '//div[contains(@class, "brand-list")]//div[contains(@class, "row")]').click() #переход в первый бренд
		brand_changer = self.driver.wait_for_element_present('//span[contains(@data-bind, "click: emex.find.brandList.showBrandsDialog")]', 'xpath', timeout=10)
		
		collect_info()
		
		brand_changer.click()
		brands_row = self.driver.find_elements('xpath', '//div[contains(@class, "brand-list")]//div[contains(@class, "row")]')
		
		for i in range(1, len(brands_row)):
			if i % 2:
				self.driver.sleep(1)
			else:
				self.driver.sleep(3)
			if i == 1:
				brands_row[1].click()
			else:
				self.driver.find_elements('xpath', '//div[contains(@class, "brand-list")]//div[contains(@class, "row")]')[i].click()
			brand_changer = self.driver.wait_for_element_present('//span[contains(@data-bind, "click: emex.find.brandList.showBrandsDialog")]', 'xpath', timeout=10)
			
			collect_info()
			
			if i != len(brands_row)-1:
				brand_changer.click()
		
		return brands, descriptions, list(set(analogs_descriptions_list)), extra_oems
			
	
	def regular_oem_func(self, main_oem):
		oem_blocks = self.driver.find_elements('xpath', "//div[contains(@class, 'original-list')]//div[contains(@class, 'expandable-list')]")
		
		brand_oem_list = [] #результаты поиска по оригинальному бренду мейн оема
		analogs_description_list = []
		extra_oems_list = []
		final_extra_oems_list = []
		for oem_block in oem_blocks:
			
			brand = oem_block.find_element('xpath', './/span[contains(@class, "detail-make")]').text
			oem = self.delete_wrong_symbols(oem_block.find_element('xpath', ".//div[contains(@class, 'detail-numbers')]/div[contains(@data-bind,'linkOrText: { text: detailInfo.VisibleNum, href: emex.find.brand.replacementSearchlUrl(detailInfo) }')]").text)
			description = oem_block.find_element('xpath', './/div[contains(@class, "one-string")]').text
			if description:
				analogs_description_list.append(description)

			try:
				extra_oem = self.delete_wrong_symbols(oem_block.find_element('xpath', ".//div[contains(@class, 'replace-number')]").text)
			except NoSuchElementException:
				extra_oem = None

			if main_oem == oem:
				main_brand = brand
				main_description = description
				extra_oems_list.append(main_oem)
				if extra_oem:
					extra_oems_list.append(extra_oem)	

			oem_block_dict = {
				"oem":oem,
				"extra_oem":extra_oem,
			}
			brand_oem_list.append(oem_block_dict)
		
		while extra_oems_list:
			checked_extra_oem = extra_oems_list.pop(0)
			if main_oem != checked_extra_oem:
				final_extra_oems_list.append(checked_extra_oem)
			for oem_block_dict in brand_oem_list:
				sub_oem = oem_block_dict["oem"]
				sub_extra_oem = oem_block_dict["extra_oem"]

				if (checked_extra_oem == sub_oem) and (sub_extra_oem != None) and (sub_extra_oem not in extra_oems_list) and (sub_extra_oem not in final_extra_oems_list):
					extra_oems_list.append(sub_extra_oem)
				if (checked_extra_oem == sub_extra_oem) and (sub_oem not in extra_oems_list) and (sub_oem not in final_extra_oems_list):
					extra_oems_list.append(sub_oem)

		return main_brand, main_description, list(set(analogs_description_list)), final_extra_oems_list
	
	@benchmark
	def analog_oem_func(self):
		
		analogs_list = []
		analog_blocks = self.driver.find_elements('xpath', "//div[contains(@data-bind, 'visible: sections.AnalogDetails.isVisible')]//div[contains(@class, 'make-group expandable-list')]")
		for analog_block in analog_blocks:
			analog_brand = analog_block.find_element('xpath', './/span[contains(@class, "detail-make")]').text.strip()
			analog_number = analog_block.find_element('xpath', './/div[contains(@data-bind, "linkOrText: { text: detailInfo.VisibleNum, href: emex.find.brand.replacementSearchlUrl(detailInfo) }")]').text.strip()
			analog_description = analog_block.find_element('xpath', './/div[contains(@class, "one-string")]').text.strip()
			row_result = analog_brand + ' && ' + analog_number + ' && ' + analog_description
			analogs_list.append(row_result)
		return analogs_list
	
	def first_page(self, sku, main_oem):
		
		if sku % 2 == 0:
			self.driver.sleep(1)
		else:
			self.driver.sleep(3)
		
		#вызов первой страницы
		self.driver.open(f'https://emex.ru/f?detailNum={main_oem}&packet=-1')
		title = self.driver.get_title().lower()
		timeout_timer = 0
		while title == 'результаты поиска' or timeout_timer == 30:
			self.driver.sleep(1)
			title = self.driver.get_title().lower()
			timeout_timer += 1

		if title == 'результаты поиска': #таймаут
			print('таймаут')
			row = [f'SKU{sku}', main_oem, 'timeout', 'timeout', 'timeout', 'timeout']
			# self.save_to_csv(row) #создать функцию
		elif self.driver.is_element_visible("div[class='no-results'][style='']"): #нет в emex
			print('нет в emex')
			row = [f'SKU{sku}', main_oem, 'нет в emex', 'нет в emex', 'нет в emex', 'нет в emex']
			# self.save_to_csv(row) #создать функцию
		elif title == 'найдено несколько совпадений': #много брендов
			print('много брендов')
			brands, descriptions, analogs_descriptions_list, extra_oems = self.some_brands_func(main_oem)
			row = [f'SKU{sku}', main_oem, ' // '.join(brands), ' // '.join(descriptions), ' // '.join(analogs_descriptions_list), ' // '.join(extra_oems)]
			self.save_to_csv(row)
		else: #обычный оем
			print('обычный оем')
			main_brand, main_description, analog_descriptions_list, final_extra_oems_list = self.regular_oem_func(main_oem)
			# analogs_list = self.analog_oem_func() #функциональность аналогов (но долгое время работы)
			row = [f'SKU{sku}', main_oem, main_brand, main_description, ' // '.join(analog_descriptions_list), ', '.join(final_extra_oems_list)]
			self.save_to_csv(row)


if __name__ == '__main__':
	test = Parser()
