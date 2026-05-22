import json
import graphviz
import os
from collections import deque

class ConfigPDA:
    def __init__(self, estado, entrada_restante, pila):
        self.estado = estado
        self.entrada_restante = entrada_restante
        self.pila = pila  # Lista donde el último elemento es el TOPE de la pila

class AutomataPila:
    def __init__(self):
        self.estados = []
        self.alfabeto = []
        self.alfabeto_pila = []
        self.estado_inicial = None
        self.simbolo_inicial_pila = 'Z'
        self.estados_finales = []
        # transitions[(estado, char_entrada, char_pop)] = [(nuevo_estado, string_push)]
        self.transiciones = {} 

    def agregar_transicion(self, estado, char_in, char_pop, nuevo_estado, string_push):
        clave = (estado, char_in, char_pop)
        if clave not in self.transiciones:
            self.transiciones[clave] = []
        self.transiciones[clave].append((nuevo_estado, string_push))

    def paso_simulacion(self, config_actual):
        nuevas_configs = []
        estado = config_actual.estado
        entrada = config_actual.entrada_restante
        pila = config_actual.pila.copy()

        # Obtener el tope de la pila (o epsilon si está vacía)
        tope = pila.pop() if pila else 'ε'
        
        # Leer el siguiente carácter (si hay)
        char_in = entrada[0] if entrada else 'ε'

        # Buscar transiciones posibles (incluyendo transiciones epsilon)
        caminos_posibles = []
        if (estado, char_in, tope) in self.transiciones:
            caminos_posibles.extend([ (t, char_in) for t in self.transiciones[(estado, char_in, tope)] ])
        if (estado, 'ε', tope) in self.transiciones:
            caminos_posibles.extend([ (t, 'ε') for t in self.transiciones[(estado, 'ε', tope)] ])

        # Generar las nuevas configuraciones hijas
        for (nuevo_estado, string_push), char_consumido in caminos_posibles:
            nueva_pila = pila.copy()
            # Apilar los nuevos símbolos (si no es epsilon)
            # Se apilan de derecha a izquierda para que el primer char quede en el tope
            if string_push != 'ε':
                for s in reversed(list(string_push)):
                    nueva_pila.append(s)
            
            nueva_entrada = entrada[1:] if char_consumido != 'ε' and entrada else entrada
            
            nuevas_configs.append(ConfigPDA(nuevo_estado, nueva_entrada, nueva_pila))
            
        return nuevas_configs
    
    def simular_paso_a_paso(self, cadena):
        """
        Genera todos los caminos de simulación (no determinista) en forma de árbol.
        Retorna una lista de configuraciones inicial, y luego se puede navegar.
        Para una interfaz paso a paso, es mejor usar un generador que explore primero
        un camino (DFS) y permita al usuario elegir entre ramas.
        Aquí implementamos una versión simple que retorna la primera aceptación encontrada
        y la secuencia de configuraciones.
        """
        from copy import deepcopy
        config_inicial = ConfigPDA(self.estado_inicial, cadena, [self.simbolo_inicial_pila])
        visitados = set()  # Para evitar ciclos (estado, entrada_restante, pila_tope)
        camino = [config_inicial]
        
        def _dfs(config):
            # Usamos tupla (estado, entrada, tope_pila) como marca de visitado
            tope = config.pila[-1] if config.pila else 'ε'
            clave = (config.estado, config.entrada_restante, tope)
            if clave in visitados:
                return None
            visitados.add(clave)
            
            if config.entrada_restante == "" and config.estado in self.estados_finales:
                return [config]
            
            nuevas = self.paso_simulacion(config)
            for sig in nuevas:
                res = _dfs(sig)
                if res is not None:
                    return [config] + res
            return None
        
        resultado = _dfs(config_inicial)
        if resultado:
            return resultado, True
        else:
            return [config_inicial], False
    
    def cargar_desde_json(self, ruta_archivo: str) -> bool:
        """Carga la definición completa de un autómata de pila desde JSON."""
        try:
            with open(ruta_archivo, 'r', encoding='utf-8') as f:
                datos = json.load(f)

            self.estados = datos.get("estados", [])
            self.alfabeto = datos.get("alfabeto", [])
            self.alfabeto_pila = datos.get("alfabeto_pila", [])
            self.estado_inicial = datos.get("inicial", None)
            self.simbolo_inicial_pila = datos.get("simbolo_inicial_pila", "Z")
            self.estados_finales = datos.get("finales", [])
            self.transiciones.clear()

            for t in datos.get("transiciones", []):
                # t: {"origen": str, "simbolo_entrada": str, "pop": str, "destino": str, "push": str}
                key = (t["origen"], t["simbolo_entrada"], t["pop"])
                if key not in self.transiciones:
                    self.transiciones[key] = []
                self.transiciones[key].append((t["destino"], t["push"]))
            return True
        except Exception as e:
            print(f"Error al cargar JSON: {e}")
            return False

    def exportar_json(self, ruta_archivo: str) -> bool:
        """Guarda la definición del autómata en JSON."""
        try:
            transiciones_lista = []
            for (estado, char_in, pop), destinos in self.transiciones.items():
                for (destino, push) in destinos:
                    transiciones_lista.append({
                        "origen": estado,
                        "simbolo_entrada": char_in,
                        "pop": pop,
                        "destino": destino,
                        "push": push
                    })
            datos = {
                "estados": self.estados,
                "alfabeto": self.alfabeto,
                "alfabeto_pila": self.alfabeto_pila,
                "inicial": self.estado_inicial,
                "simbolo_inicial_pila": self.simbolo_inicial_pila,
                "finales": self.estados_finales,
                "transiciones": transiciones_lista
            }
            with open(ruta_archivo, 'w', encoding='utf-8') as f:
                json.dump(datos, f, indent=4)
            return True
        except Exception:
            return False
        
    def generar_grafo(self, nombre_archivo="grafo_pda"):
        """Genera una imagen PNG del autómata de pila usando Graphviz."""
        dot = graphviz.Digraph(format='png')
        dot.attr(rankdir='LR', bgcolor='transparent')
        dot.attr('node', fontcolor='white', color='white')
        dot.attr('edge', fontcolor='white', color='white')
        
        dot.node('start', shape='point')
        
        for q in self.estados:
            if q in self.estados_finales:
                dot.node(q, shape='doublecircle')
            else:
                dot.node(q, shape='circle')
        
        if self.estado_inicial:
            dot.edge('start', self.estado_inicial)
        
        # Agrupar transiciones iguales (origen->destino) con etiqueta compuesta
        agrupaciones = {}
        for (origen, char_in, pop), destinos in self.transiciones.items():
            for (destino, push) in destinos:
                key = (origen, destino)
                label = f"{char_in}, {pop} → {push}"
                if key not in agrupaciones:
                    agrupaciones[key] = []
                agrupaciones[key].append(label)
        
        for (origen, destino), etiquetas in agrupaciones.items():
            etiqueta = ", ".join(etiquetas)
            dot.edge(origen, destino, label=etiqueta)
        
        dot.render(nombre_archivo, cleanup=True)
        return os.path.abspath(f"{nombre_archivo}.png")
        
    def obtener_siguientes_configs(self, config_actual):
        """Devuelve una lista de ConfigPDA posibles a partir de la actual."""
        return self.paso_simulacion(config_actual)

    def reiniciar_simulacion(self, cadena):
        """Crea la configuración inicial para una nueva simulación."""
        return ConfigPDA(self.estado_inicial, cadena, [self.simbolo_inicial_pila])
    
    def limpiar_automata(self):
        """Restablece todas las propiedades para construir un nuevo autómata desde cero."""
        self.estados = []
        self.alfabeto = []
        self.alfabeto_pila = []
        self.estado_inicial = None
        self.simbolo_inicial_pila = 'Z'
        self.estados_finales = []
        self.transiciones.clear()