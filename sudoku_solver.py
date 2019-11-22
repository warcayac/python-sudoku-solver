# -----------------------------------------------------------
# SUDOKU SOLVER by using OOP with Python 3.8 or later
#
# (C) 2019 William Arcaya Carpio, Perú
# Released under MIT License
# eMail: warcayac@gmail.com
#
# Published: November 20, 2019
# OS tested: Ubuntu (linux)
# -----------------------------------------------------------

from pathlib import Path
from itertools import combinations
import re 
import time
# from sys import setrecursionlimit		# default recursion limit = 10^4

_BOARD_RANGE = range(9)
_BLOCK_RANGE = range(3)
_VALID_DIGITS = list(range(1, 10))
_STARTING_COUNTER = dict(zip(_VALID_DIGITS, (9,)*len(_VALID_DIGITS)))

#####################################################################################################
#####################################################################################################

class FColors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

#####################################################################################################
#####################################################################################################

class SudokuBoard:
	#-------------------------------------------------------------------------------#
	def __init__(self):
		self.__cells = []
		self.__quadrants = []
		self.__rows = []
		self.__columns = []
		self.__step = 0		# incrementa en 1 por celda-solución encontrada
	#-------------------------------------------------------------------------------#
	def __build_board(self):
		# Defines
		_MatrixOf = lambda ownerObj,classType,scope: [[classType(ownerObj) for c in scope] for r in scope]
		_VectorOf = lambda ownerObj,classType,scope: [classType(ownerObj) for i in scope]
		# Ejecutas
		Cell.unique_candidates.clear()
		self.__columns.clear()
		self.__rows.clear()
		self.__quadrants.clear()
		self.__cells.clear()
		self.__cells = _MatrixOf(self, Cell, _BOARD_RANGE)
		self.__quadrants = _VectorOf(self, Quadrant, _BOARD_RANGE)
		self.__rows = _VectorOf(self, Row, _BOARD_RANGE)
		self.__columns = _VectorOf(self, Column, _BOARD_RANGE)
		self.__link_cells_to_sectors()
	#-------------------------------------------------------------------------------#
	def __load_data(self, sequence, restoring=False, /):
		try:
			for i,value in enumerate(sequence):
				if value.isnumeric() and int(value) > 0:
					cell = self.__cells[i // 9][ i % 9]
					cell.value = int(value)
					if not restoring: cell.is_given = True
					# print(f"Cell[{i//9},{i%9}] = {value}",">"*20)
					# self.__show_availability_per_sector()
			return True
		except NoCandidatesError as e:
			print("[ERROR] Tablero inconsistente.", e)
			return False
	#-------------------------------------------------------------------------------#
	def show_board(self, boardN, can_show, /):
		"""
		Método para visualizar el estado de un tablero Sudoku.
		
		ARGS:
		- can_show	: (bool) permite la visualización de tablero.
		- boardN	: (int) número de tablero siendo procesado su solución.
		"""
		if can_show:
			print("*"*30, f"[ BOARD Nº {boardN}: STEP {self.__step} ]", "*"*30)
			for row in _BOARD_RANGE:
				if row and not (row % 3): print("───┼───┼───")
				for col in _BOARD_RANGE:
					if col and not (col % 3): print("|", end="")
					cell = self.__cells[row][col]
					print(cell if cell.value else "·", end="")
				print("")
	#-------------------------------------------------------------------------------#
	def __link_cells_to_sectors(self):
		for r in _BOARD_RANGE:
			for c in _BOARD_RANGE:
				quadrant = self.__quadrants[(r//3)*3+(c//3)]
				cell = self.__cells[r][c]
				quadrant.cells.append(cell)
				cell._from_quadrant = quadrant
				cell.pos = (r,c)
		for r in _BOARD_RANGE:
			self.__rows[r].cells.extend(self.__cells[r])
			for c in _BOARD_RANGE:
				self.__cells[r][c]._from_row = self.__rows[r]
		for c in _BOARD_RANGE:
			for r in _BOARD_RANGE:
				self.__columns[c].cells.append(self.__cells[r][c])
				self.__cells[r][c]._from_column = self.__columns[c]
	#-------------------------------------------------------------------------------#
	def __trace_single_frequency_values(self, way, show_by_step, showing, boardN, /):
		"""
		Método privado que ratrea candidatos de frecuencia por sección.
		
		ARGS:
		- way		: (int) modo de rastreo, por cuadrante/fila/columna.
		- showing	: (bool) permite la visualización de tableros intermedios y final.
		- show_by_step	: (int) cada cuántos pasos/asignaciones se mostrará el estado del
				tablero Sudoku siendo resuelto. Omitido si se un lote de tableros, 
				en tal caso sólo llega a mostrar el tablero final.
		- boardN	: (int) número de tablero siendo procesado su solución.
		"""
		# Definiendo variables
		BY_QUADRANT, BY_ROW, BY_COLUMN = _BLOCK_RANGE
		d = "Cuadrante" if way==BY_QUADRANT else "Fila" if way==BY_ROW else "Columna"
		# Seleccionar los sectores a procesar
		sectors = self.__quadrants if way==BY_QUADRANT else self.__rows if way==BY_ROW else self.__columns
		# Iniciar al barrido por fila/columna
		cell = None
		change_exists = False
		targets = {}
		# Escanear a través de cada unidad (cuadrante/fila/columna) del sector seleccionado
		for i in _BOARD_RANGE:
			targets.clear()
			sector = sectors[i]
			# en el presente sector, ¿hay candidatos de frecuencia única?
			if 1 in sector._available.values():
				# para cada candidato de frecuencia única...
				for unique in [k for k,v in sector._available.items() if v==1]:
					# escanear celdas que componen el sector en curso
					for j in _BOARD_RANGE:
						cell = sector.cells[j]
						# ¿celda contiene candidato de frecuencia única?
						if unique in cell._candidates:
							if cell not in targets:
								targets[cell] = unique
								break	# salir del FOR en curso
							else:
								raise Exception(f"[{d}] Celda contiene más de un candidato único.")
				# tratar celdas con candidatos de frecuencia única
				cell = unique = None
				if targets:
					change_exists = True
					# establecer únicos como solución para su celda origen
					for cell, unique in targets.items():
						self.__step += 1
						cell.value = unique
						self.show_board(boardN, showing and show_by_step and not (self.__step % show_by_step))
		return change_exists
	#-------------------------------------------------------------------------------#
	def __apply_naked_hidden_twins_technique(self):
		change_exists = False
		for i in _BOARD_RANGE: # por cada cuadrante
			# identificar celdas que contienen candidatos de frecuencia 2 en el cuandrante
			quadrant = self.__quadrants[i]
			old_counter = quadrant._available.copy()
			twos = [k for k,v in quadrant._available.items() if v==2]
			if twos:
				targets = {x:[] for x in twos}
				for j in _BOARD_RANGE: # por cada celda en el cuadrante
					cell = quadrant.cells[j]
					shared = list(set(cell._candidates).intersection(set(twos)))
					# recolectar celdas que contienen candidatos de frecuencia 2
					if cell._candidates and shared:
						for key in shared:
							targets[key].append(cell)
				# si un candidato aparece 2 veces en un misma fila/columna,
				# eliminar ese candidato del resto de celdas de esa fila/columna
				for key,cells in targets.items():
					if cells[0].pos['row'] == cells[1].pos['row']: # comparar filas
						cells[0]._from_row._remove_candidate_from_sector(key, cells)
					elif cells[0].pos['col'] == cells[1].pos['col']: # comparar columnas
						cells[0]._from_column._remove_candidate_from_sector(key, cells)
				# si dos pares de candidatos aparecen en las mismas dos celdas, 
				# eliminar resto de candidatos en ambas celdas
				if len(twos) > 1:
					for k1, k2 in combinations(twos, 2):
						if not len(set(targets[k1])-set(targets[k2])):
							cell1,cell2 = targets[k1]
							cell1._remove_candidates_from_cell(list(set(cell1._candidates)-{k1,k2}))
							cell2._remove_candidates_from_cell(list(set(cell2._candidates)-{k1,k2}))
			change_exists = change_exists or (old_counter != quadrant._available)
		# self.__show_candidates()
		# self.__show_availability_per_sector()
		return change_exists
	#-------------------------------------------------------------------------------#
	def __restore_board_by_using_sequence(self, sequence, step, /):
		# Reiniciar contadores de todas las secciones
		for i in _BOARD_RANGE:
			self.__quadrants[i]._available = _STARTING_COUNTER.copy()
			self.__rows[i]._available = _STARTING_COUNTER.copy()
			self.__columns[i]._available = _STARTING_COUNTER.copy()
		# Reiniciar candidatos de celdas y valores de celdas
		for r in _BOARD_RANGE:
			for c in _BOARD_RANGE:
				cell = self.__cells[r][c]
				cell._candidates = _VALID_DIGITS.copy()
				cell.value = None
		# Cargar secuencia
		self.__load_data(sequence, True)
		self.__step = step
		# Vaciar lista de candidatos únicos
		Cell.unique_candidates.clear()
	#-------------------------------------------------------------------------------#
	def __make_decisions(self):
		#---------------------------------------------------------------#
		def detect_starting_cell_to_make_decision():
			# ¿cuál es la menor cantidad de candidatos que tiene una celda en el tablero presente?
			min_base = 9
			for quadrant in self.__quadrants:
				# Identificar los candidatos con frecuencia 2 en el cuadrante
				twins = [k for k,v in quadrant._available.items() if v==2]
				shared = 0
				for cell in quadrant.cells:
					if 1 < (l:= len(cell._candidates)) < min_base:
						min_base = l
					if len(twins) > 1 and l > 1:
						shared = len(set(cell._candidates).intersection(set(twins)))
						if shared == 2 and l==2: break
						shared = 0
				if shared == 2 and l == 2: break
				cell = None
			# Si se encontró una celda bajo condiciones de paridad...
			if shared == 2 and l == 2 and cell: return cell
			# caso contrario, retornar la celda con el mínimo de canditatos
			for quadrant in self.__quadrants:
				for cell in quadrant.cells:
					if len(cell._candidates) == min_base: return cell
			return None
		#---------------------------------------------------------------#
		def make_a_decision_on_the_candidate(option, row, col, /):
			decision_was_right = True
			self.__cells[row][col].value = option
			# print(f"     Opción seleccionada: {option}")
			try:
				self.__solve(False, 0, 0, True)
				# print(f"     Opción {option}... Correcta")
			except Exception:
				# print(f"     Opción {option}... Fallida")
				decision_was_right = False
			finally:
				return decision_was_right
		#---------------------------------------------------------------#
		# Seleccionar la celda de donde se empezarán a tomar decisiones
		if not (cell:= detect_starting_cell_to_make_decision()): 
			raise InconsistentBoardError("No se encuentra un camino de solución al tablero.")
		# Obtener data necesaria para propósitos de restauración/decisión
		BASE_BOARD_SEQ = self.get_current_sequence()
		BASE_STEP = self.__step
		OPTIONS = cell._candidates.copy()
		row = cell.pos['row']
		col = cell.pos['col']
		# self.show_board(0,True)
		# print(f"Tomando decisiones sobre los candidatos {cell._candidates} de la celda {cell.pos}")
		cell = None
		# Probar cada opción para saber cuál conduce al tablero solución
		for i, option in enumerate(OPTIONS):
			if i: 
				# self.show_board(0,True)				
				self.__restore_board_by_using_sequence(BASE_BOARD_SEQ, BASE_STEP)
			if (is_right:= make_a_decision_on_the_candidate(option, row, col)): break
		if not is_right:
			raise InconsistentBoardError(f"Candidatos {OPTIONS} conducen a un tablero inconsistente.")
#-------------------------------------------------------------------------------#
	def __solve(self, showing, show_by_step, boardN, recursive=False, /):
		"""
		Método privado que procesa la solución a un tablero Sudoku.
		
		ARGS:
		- showing	: (bool) permite la visualización de tableros intermedios y final.
		- show_by_step	: (int) cada cuántos pasos/asignaciones se mostrará el estado del
				tablero Sudoku siendo resuelto. Omitido si se un lote de tableros, 
				en tal caso sólo llega a mostrar el tablero final.
		- boardN	: (int) número de tablero siendo procesado su solución.
		- recursive	: (bool) indica si el proceso se ejecuta en modo recursivo.
		"""
		if show_by_step < 0: show_by_step = 0
		if not recursive: self.__step = 0
		twins_applied = False
		made_decision = False
		while True:
			# Tratar candidatos únicos en celda
			while Cell.unique_candidates:
				cell = Cell.unique_candidates.pop(0)
				if cell._candidates:
					self.__step += 1
					cell.value = cell._candidates[0]
					self.show_board(boardN, showing and show_by_step and not (self.__step % show_by_step))
				cell = None
			
			# Localizar candidatos únicos por cuadrante (0), fila (1), columna (2)
			rescan = True
			while rescan and not Cell.unique_candidates:
				rescan = False
				for way in _BLOCK_RANGE:
					rescan = rescan or self.__trace_single_frequency_values(way, show_by_step, showing, boardN)
				if rescan: twins_applied = False
			if Cell.unique_candidates: continue
			if self.is_solved(): break

			# Aquí se llega sin candidatos únicos ni candidatos de frecuencia única en todos los sectores
			# Aplicar técnica de pares gemelos (naked/hidden twins) por cuadrante
			if not twins_applied:
				rescan = True
				num_try = 0
				while rescan and not Cell.unique_candidates:
					num_try += 1
					rescan = self.__apply_naked_hidden_twins_technique()
				if Cell.unique_candidates: continue
				# si el tablero no tiene cambios en sus candidatos tras aplicar la técnica en su primer
				# intento, entonces se debe aplicar el proceso de prueba-error inmediatamente
				if num_try==1: break
				# ya que hubo cambios en los candidatos del tablero, hacer un nuevo chequeo en busca de 
				# celdas-solución. Si tras el chequeo no hay cambio alguno en el tablero, ya no debería
				# ejecutarse esta técnica, y debería salirse del bucle presente.
				twins_applied = True
			else:
				break	# termina el WHILE padre

		# Iniciar proceso de prueba-error si el tablero no ha sido resuelto
		if not self.is_solved(): 
			self.__make_decisions()
			made_decision = True
		# Mostrar tablero final
		if not recursive:
			self.show_board(boardN, showing and (made_decision or not (show_by_step and not (self.__step % show_by_step))))
	#-------------------------------------------------------------------------------#
	def __parse_sequence(self, data):
		# https://www.technologyreview.com/s/426554/mathematicians-solve-minimum-sudoku-problem
		minimum_numbers_given = 17
		values_per_board = 81
		seq = re.sub(r'\s+', '', data)
		return (seq, len(seq) == values_per_board and len(re.findall(r'[1-9]', seq)) >= minimum_numbers_given)
	#-------------------------------------------------------------------------------#
	def is_solved(self):
		for i in _BOARD_RANGE:
			if not self.__quadrants[i]._solved():
				return False
		return True
	#-------------------------------------------------------------------------------#
	def solve_from(self, source, /, show_by_step:int=0, show_boards=True, sep="\n", text=""):
		"""
		Método principal llamado para dar solución a tablero(s) Sudoku.
		
		ARGS:
		- source	: (str) cadena de texto representando: (1) una secuencia fija de 81 
				caracteres alfanuméricos, ó (2) la localización del archivo conteniendo 
				secuencias de tableros Sudoku.
		- show_by_step	: (int) cada cuántos pasos/asignaciones se mostrará el estado del
				tablero Sudoku siendo resuelto. Omitido si se un lote de tableros, en tal 
				caso sólo llega a mostrar el tablero final.
		- show_boards	: (bool) permite la visualización de tableros intermedios y final.
		- sep		: (str) separador entre secuencias, útil si 'source' es un archivo.
		- text		: (str) texto a agregar al sumario estadístico final.
		"""
		if source:
			if type(source) == str:
				try:
					# Si no es una secuencia, es archivo, entonces extraer todas las secuencias
					if not self.__parse_sequence(source)[1]:
						sourcefile = Path(source)
						if not sourcefile.exists(): 
							raise FileNotFoundError("File not found.")
						else:
							with sourcefile.open() as sf:
								source = sf.read().strip().split(sep)
							if not source: raise ValueError("File empty.")
					else:
						source = [source,]
					# Si se procesa más de un tablero, no mostrar soluciones parciales
					if len(source) > 1: show_by_step = 0
					# Resolver tableros
					csolved = cout = cunsolved = 0
					times = []
					# Extraer cada secuencia y resolverla, midiendo su tiempo de ejecución
					for i, seq in enumerate(source, 1):
						seq, flag = self.__parse_sequence(seq)
						if flag:
							self.__build_board()
							if self.__load_data(seq):
								if show_boards: print(seq)
								self.show_board(i, show_boards and show_by_step)
								time_start = time.perf_counter()
								try:
									self.__solve(show_boards, show_by_step, i)
								except Exception as e:
									self.show_board(i, show_boards and not show_by_step)
									print(f"[{type(e).__name__}] {e}")
								finally:
									delta_time = time.perf_counter() - time_start
								if show_boards:
									print("({:.5f} seconds)\n".format(delta_time))
								if self.is_solved():
									csolved += 1
									times.append(delta_time)
								else: 
									cunsolved += 1
							else: cout += 1
						else: cout += 1
					# Mostrar sumario estadístico al finalizar todo el proceso
					size = len(source)
					if times:
						print("Excluded {}, Unsolved {}, Solved {} of {} {} puzzles (avg {:.5f} secs ({:.0f} Hz), max {:.5f} secs)".format(
							cout, cunsolved, csolved, size, text, sum(times)/size, size/sum(times), max(times)))
					else:
						print("Excluded {}, Unsolved {}, Solved {} of {} {} puzzles".format(
							cout, cunsolved, csolved, size, text))
				except Exception as e:
					print(f"[{type(e).__name__}] {e}")
			else:
				raise TypeError("Data type is not a string.")
	#-------------------------------------------------------------------------------#
	def get_current_sequence(self):
		seq = ""
		for r in _BOARD_RANGE:
			for c in _BOARD_RANGE:
				value = self.__cells[r][c].value
				seq += str(value) if value else "0"
		return seq
	#-------------------------------------------------------------------------------#
	def __check_links(self): # sólo para propósitos de verificación
		# Checking rows
		for x in _BOARD_RANGE:
			flag = True
			for y in _BOARD_RANGE:
				cell = self.__cells[x][y]
				row = self.__rows[x]
				flag = flag and (cell is row.cells[y]) and (cell._from_row is row)
			print(f"Row {x}... {'passed' if flag else 'failed'}")
		# Checking columns
		for x in _BOARD_RANGE:
			flag = True
			for y in _BOARD_RANGE:
				cell = self.__cells[y][x]
				col = self.__columns[x]
				flag = flag and (cell is col.cells[y]) and (cell._from_column is col)
			print(f"Column {x}... {'passed' if flag else 'failed'}")
		# Checking quadrants
		for i in range(3): # por filas de cuadrantes
			for j in range(3): # por columnas de cuadrantes
				flag = True
				k = 0
				for x in range(0+i*3,3+i*3):
					for y in range(0+j*3,3+j*3):
						cell = self.__cells[x][y]
						quad = self.__quadrants[3*i+j]
						flag = flag and (cell is quad.cells[k]) and (cell._from_quadrant is quad)
						k += 1
				print(f"Quadrant {3*i+j}... {'passed' if flag else 'failed'}")
	#-------------------------------------------------------------------------------#
	def __show_candidates(self): # sólo para propósitos de verificación
		for r in _BOARD_RANGE:
			print("="*30)
			for c in _BOARD_RANGE:
				print(f"[{r},{c}] --> {self.__cells[r][c]._candidates}")
	#-------------------------------------------------------------------------------#
	def __show_availability_per_sector(self): # sólo para propósitos de verificación
		# rows
		print("="*30)
		for i in _BOARD_RANGE:
			print(f"Row {i} --> counter: {self.__rows[i]._available}")
		# columns
		print("="*30)
		for i in _BOARD_RANGE:
			print(f"Column {i} --> counter: {self.__columns[i]._available}")
		# quadrants
		print("="*30)
		for i in _BOARD_RANGE:
			print(f"Quadrant {i} --> counter: {self.__quadrants[i]._available}")

#####################################################################################################
#####################################################################################################

class Sector:
	def __init__(self, owner:SudokuBoard):
		self._owner = owner
		# Números disponibles dentro del sector
		self._available = _STARTING_COUNTER.copy()
		self.cells = []
	#-------------------------------------------------------------------------------#
	def _remove_candidate_from_sector(self, value, avoid:list=[], /):
		if not self._solved():
			for cell in set(self.cells)-set(avoid):
				if value in cell._candidates: # omite celdas con valores asignados
					cell._remove_candidates_from_cell(value)
					# if not cell._candidates:
					# 	raise NoCandidatesError(f"Celda {cell.pos} se ha quedado sin valores candidatos")
					cell._check_uniqueness()
	#-------------------------------------------------------------------------------#
	def _update_availability_in_sector(self, keys):
		if type(keys) == list:
			for k in keys:
				self._available[k] -= 1
		elif type(keys) == int:
			self._available[keys] -= 1
		else:
			raise TypeError("Tipo de dato no aceptado.")
	#-------------------------------------------------------------------------------#
	def _solved(self):
		return set(self._available.values()) == {0}

#####################################################################################################
#####################################################################################################

class Row(Sector): pass
class Column(Sector): pass
class Quadrant(Sector): pass
class NoCandidatesError(Exception): pass
class InconsistentBoardError(Exception): pass

#####################################################################################################
#####################################################################################################

class Cell:
	#-------------------------------------------------------------------------------#
	unique_candidates = []		# class attribute/variable
	#-------------------------------------------------------------------------------#
	def __init__(self, owner:SudokuBoard):
		self._owner = owner
		self._candidates = _VALID_DIGITS.copy()
		self.__value = None
		self.is_given = False
		self._from_quadrant = self._from_row = self._from_column = None
		self.__posRC = None
	#-------------------------------------------------------------------------------#
	def __str__(self):
		if self.__value:
			return str(self.__value) if not self.is_given else f"{FColors.FAIL}{self.__value}{FColors.ENDC}"
		else:
			return ""
	# -------------------------------------------------------------------------------#
	# a getter function
	@property
	def value(self):
		return self.__value
	#-------------------------------------------------------------------------------#
	# a setter function
	@value.setter
	def value(self, value):
		self.__value = value
		if value != None:
			self._remove_candidates_from_cell(self._candidates.copy())
			self.__propagate_candidate_removal_through_sectors(value)
	#-------------------------------------------------------------------------------#
	@property
	def pos(self):
		return self.__posRC
	#-------------------------------------------------------------------------------#
	@pos.setter
	def pos(self, value):
		if type(value)==tuple and len(value)==2:
			if self.__posRC is None:
				self.__posRC = dict(row=value[0], col=value[1])
		else:
			raise TypeError("Se esperaba una tupla de par de dígitos numéricos válidos.")
	#-------------------------------------------------------------------------------#
	def _check_uniqueness(self):
		if self.value is None:
			if len(self._candidates) == 1:
				if self not in Cell.unique_candidates:
					Cell.unique_candidates.append(self)
			if len(self._candidates) == 0:
				raise NoCandidatesError(f"Celda {self.pos} se ha quedado sin valores candidatos")
	#-------------------------------------------------------------------------------#
	def __propagate_candidate_removal_through_sectors(self, value):
		self._from_quadrant._remove_candidate_from_sector(value)
		self._from_row._remove_candidate_from_sector(value)
		self._from_column._remove_candidate_from_sector(value)
	#-------------------------------------------------------------------------------#
	def _remove_candidates_from_cell(self, values):
		if type(values) == int:
			self._candidates.remove(values)
		elif type(values) == list:
			self._candidates = list(set(self._candidates)-set(values))
		else:
			raise TypeError("Tipo de dato no aceptado.")
		# update availability in sectors
		self._from_quadrant._update_availability_in_sector(values)
		self._from_row._update_availability_in_sector(values)
		self._from_column._update_availability_in_sector(values)

#####################################################################################################
#####################################################################################################

if __name__ == '__main__':
	Puzzle = SudokuBoard()
	# Puzzle.solve_from("_1______3______________46_7_9__________1_3____43___8_56__8___2___7_5_98___5_4_7__", 
	# 	text="expert", show_boards=True, show_by_step=0)
	# Puzzle.solve_from("_7_25_4__8_____9_3_____3_7_7____4_2_1_______7_4_5____8_9_6_____4_1_____5__7_82_3_", 
	# 	text="diabolical", show_boards=True, show_by_step=0)
	# Puzzle.solve_from(".....5.8....6.1.43..........1.5........1.6...3.......553.....61........4.........", 
	# 	text="impossible", show_boards=True, show_by_step=0)  # no solucionable, sirve para tomar tiempo de esta conclusión
	# Puzzle.solve_from("093000600000501000000000000100400050000090300000000800421000000000730000500000000", 
	# 	text="evil", show_boards=True, show_by_step=0)	# solucionable
	# Puzzle.solve_from("000700000100000000000430200000000006000509000000000418000081000002000050040000300", 
	# 	text="evil", show_boards=True, show_by_step=0) # solucionable
	# Puzzle.solve_from("000000012000000003002300400001800005060070800000009000008500000900040500470006000", 
	# 	text="Blonde Platine", show_boards=True, show_by_step=0) # solucionable
	# Puzzle.solve_from("000002750018090000000000000490000000030000008000700200000030009700000000500000080", 
	# 	text="snake17", show_boards=True, show_by_step=0)	# solucionable
	# Puzzle.solve_from(".....6....59.....82....8....45........3........6..3.54...325..6..................", 
	# 	text="hardest", show_boards=True, show_by_step=0)	# solucionable
	Puzzle.solve_from("data/easy50.txt", text="easy", show_boards=False, sep="========")
	Puzzle.solve_from("data/top95.txt", text="hard", show_boards=False)
	Puzzle.solve_from("data/hardest.txt", text="hardest", show_boards=False)
	Puzzle.solve_from("data/hardest(2019).txt", text="hardest (2019)", show_boards=False)


## References used:
## https://norvig.com/sudoku.html

## Sitios para Sudoku
## https://www.free-sudoku.com/sudoku.php?dchoix=evil