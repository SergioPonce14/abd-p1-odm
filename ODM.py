__author__ = 'Pablo Ramos Criado'
__students__ = 'Sergio Ponce Plaza e Isaac Cárdenas Resino'


from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import time
from typing import Generator, Any, Self
from geojson import Point
import pymongo
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from bson.objectid import ObjectId
import yaml

def getLocationPoint(address: str) -> Point:
    """ 
    Obtiene las coordenadas de una dirección en formato geojson.Point
    Utilizar la API de geopy para obtener las coordenadas de la direccion
    Cuidado, la API es publica tiene limite de peticiones, utilizar sleeps.

    Parameters
    ----------
        address : str
            direccion completa de la que obtener las coordenadas
    Returns
    -------
        geojson.Point
            coordenadas del punto de la direccion
    """
    location = None
    intentos = 0
    maxIntentos = 5
    while location is None and intentos < maxIntentos:
        intentos += 1
        try:
            time.sleep(1)
            #TODO
            # Es necesario proporcionar un user_agent para utilizar la API
            # Utilizar un nombre aleatorio para el user_agent
            location = Nominatim(user_agent="Mi-Nombre-Aleatorio").geocode(address)
        except GeocoderTimedOut:
            # Puede lanzar una excepcion si se supera el tiempo de espera
            # Volver a intentarlo
            continue
    #TODO
    # Devolver un GeoJSON de tipo punto con la latitud y longitud almacenadas.
    # Si no se consiguieron coordenadas, lanzar ValueError: la funcion no puede
    # devolver un punto inventado ni None silenciosamente. Es lo que espera la
    # prueba test_get_location_point_timeout_failure.

class Model:
    """ 
    Clase de modelo abstracta
    Crear tantas clases que hereden de esta clase como  
    colecciones/modelos se deseen tener en la base de datos.

    Attributes
    ----------
        required_vars : set[str]
            conjunto de atributos requeridos por el modelo
        admissible_vars : set[str]
            conjunto de atributos admitidos por el modelo
        db : pymongo.collection.Collection
            conexion a la coleccion de la base de datos
    
    Methods
    -------
        __setattr__(name: str, value: str | dict) -> None
            Sobreescribe el metodo de asignacion de valores a los 
            atributos del objeto con el fin de controlar qué atributos 
            son modificados y cuando son modificados.
        __getattr__(name: str) -> Any
            Sobreescribe el metodo de acceso a atributos del objeto 
        save()  -> None
            Guarda el modelo en la base de datos
        delete() -> None
            Elimina el modelo de la base de datos
        find(filter: dict[str, str | dict]) -> ModelCursor
            Realiza una consulta de lectura en la BBDD.
            Devuelve un cursor de modelos ModelCursor
        aggregate(pipeline: list[dict]) -> pymongo.command_cursor.CommandCursor
            Devuelve el resultado de una consulta aggregate.
        find_by_id(id: str) -> dict | None
            Busca un documento por su id utilizando la cache y lo devuelve.
            Si no se encuentra el documento, devuelve None.
        init_class(db_collection: pymongo.collection.Collection, required_vars: set[str], admissible_vars: set[str]) -> None
            Inicializa las variables de clase en la inicializacion del sistema.

    """
    _required_vars: set[str]
    _admissible_vars: set[str]
    _location_var: str | None = None
    _db: pymongo.collection.Collection
    _internal_vars: set[str] = frozenset(('_modified_vars', '_required_vars', '_admissible_vars', '_db', '_data', '_location_var'))

    def __init__(self, **kwargs: dict[str, str | dict | list]) -> None:
        #Ejemplo de llamada Evento(titulo="Gira 2026", artistas=["Quevedo"], recinto="Wizink Center",  fecha="2026-11-14", hora="21:00", precio={"general": 45})
        #**kwargs recoge los argumentos con su clave en un diccionario
        self._data: dict[str, str | dict | list] = {}#diccionario vacio donde irán los datos
        self._modified_vars = set()#conjunto vacio donde van los atributos modificadosal crear un objeto

        permitidas = set(self._required_vars) | set(self._admissible_vars) | {"_id"}#unimps los argumentos requeridos con los admitidos junto su _id
        if self._location_var:#si el location_var no es none
          permitidas.add(self._location_var + "_loc")#se añade

        faltan = self._required_vars - kwargs.keys()#calculamos si faltan atributos requeridos
        if faltan:
          raise ValueError(f"Faltan atributos requeridos: {faltan}")#si faltan salta una excepcion

        sobran = kwargs.keys() - permitidas
        if sobran:#y si sobran
         raise ValueError(f"Atributos no admitidos: {sobran}")# salta una excepcion

        self._data.update(kwargs)#añadimos el valor de kwargs en _data
        #_data quedaria así self._data = {"titulo": "Gira 2026", "artistas": ["Isaac"], "recinto": "Wizink Center", "fecha": "2026-11-14", "hora": "21:00", "precio": {"general": 45}}

    def __setattr__(self, name: str, value: str | dict) -> None:
        """ Sobreescribe el metodo de asignacion de valores a los 
        atributos del objeto con el fin de controlar que atributos 
        son modificados y cuando son modificados.
        """
        #ejemplo de hacer un set de el numero de entradas vendidas e.num_vendidas = 120
        #comprueba si el name q en este ejemplo sería num_vendidas está en el ODM
        #num_vendidas" no está ahí, así que el if no se cumple y se salta el if
        if name in self._internal_vars:
            super().__setattr__(name, value)#guarda el atributo odirectamente sin validar
            return
        
        permitidasSet = set(self._required_vars) | set(self._admissible_vars) | {"_id"}#unimos los argumentos requeridos con los admitidos junto su _id
        if self._location_var:#si es location var se guardara 
         permitidasSet.add(self._location_var + "_loc")

        if name not in permitidasSet:#si el nombre no está en el conjunto salta una excepcion
          raise ValueError(f"Atributo no admitido: {name}")
        
        # Guarda el valor en el diccionario de datos
        self._data[name] = value
        self._modified_vars.add(name) # Apunta el campo como modificado para que save() solo actualice ese

    def __getattr__(self, name: str) -> Any:
        """ Sobreescribe el metodo de acceso a atributos del objeto
        __getattr__ solo es llamado cuando no encuentra el atributo
        en el objeto 
        """
        if name in self._internal_vars:
            return super().__getattribute__(name)
        try:
            return self._data[name]
        except KeyError:
            raise AttributeError
        
    def save(self) -> None:



        """
        Guarda el modelo en la base de datos
        Si el modelo no existe en la base de datos, se crea un nuevo
        documento con los valores del modelo. En caso contrario, se
        actualiza el documento existente con los nuevos valores del
        modelo.
        """
        #primero vamos a comprobar si el modelo tiene un campo de direccion en el YAML  y si tiene valor
        if self._location_var and self._location_var in self._data:
            #buscamos coordenadas si el documento cambio o si es nuevo
            if "_id" not in self._data or self._location_var in self._modified_vars:
                coordenadas = getLocationPoint(self._data[self._location_var])
                nombre_loc = self._location_var + "_loc"
                
                self._data[nombre_loc] = coordenadas
                self._modified_vars.add(nombre_loc)
        #ahora insertamos el nuevo documento, para saber si es nuevo comprobamos si este ya tiene un id
        if "_id" not in self._data:
            self._db.insert_one(self._data)
            #limpiamos las variables modificadas al guardar
            self._modified_vars.clear()
        #si tiene id hay que actualizar
        else:
            camposActualizar={}
            for campo in self._modified_vars:
                #campo es el valor de los elementos guardados, nombre aforo...
                camposActualizar[campo]=  self._data[campo]
            self._db.update_one(
                {"_id": self._data["_id"]},
                {"$set": camposActualizar})
            #limpiamos las variables modificadas al guardar
            self._modified_vars.clear()
    def delete(self) -> None:
       if "_id" in self._data:#si tiene id
        self._db.delete_one({"_id": self._data["_id"]})#borra en mongo el documento con esa _id
    @classmethod
    def find(cls, filter: dict[str, str | dict]) -> Any:
    
        cursor = cls._db.find(filter) # en mongo buscamos con el .find(que es de mongo), que va a devolver el curdsor de mondo del resultado
        return ModelCursor(cls, cursor) # retornamos un ModelCursor al q le pasamo la clase cls y el cursor de la respustra del filtro 

    @classmethod
    def aggregate(cls, pipeline: list[dict]) -> pymongo.command_cursor.CommandCursor:
        """ 
        Devuelve el resultado de una consulta aggregate. 
        No hay nada que hacer en esta funcion.
        Se utilizara para las consultas solicitadas
        en el segundo proyecto de la practica.

        Parameters
        ----------
            pipeline : list[dict]
                lista de etapas de la consulta aggregate 
        Returns
        -------
            pymongo.command_cursor.CommandCursor
                cursor de pymongo con el resultado de la consulta
        """ 
        return cls._db.aggregate(pipeline)
    
    @classmethod
    def find_by_id(cls, id: str) -> Self | None:
        """ 
        NO IMPLEMENTAR HASTA EL TERCER PROYECTO
        Busca un documento por su id utilizando la cache y lo devuelve.
        Si no se encuentra el documento, devuelve None.

        Parameters
        ----------
            id : str
                id del documento a buscar
        Returns
        -------
            Self | None
                Modelo del documento encontrado o None si no se encuentra
        """ 
        #TODO
        pass

    @classmethod
    def init_class(cls, db_collection: pymongo.collection.Collection, indexes:dict[str,str], required_vars: set[str], admissible_vars: set[str]) -> None:
        """ 
        Inicializa los atributos de clase en la inicializacion del sistema.
        Aqui se deben inicializar o asegurar los indices. Tambien se puede
        alguna otra inicialización/comprobaciones o cambios adicionales
        que estime el alumno.

        Parameters
        ----------
            db_collection : pymongo.collection.Collection
                Conexion a la collecion de la base de datos.
            indexes: Dict[str,str]
                Set de indices y tipo de indices para la coleccion
            required_vars : set[str]
                Set de atributos requeridos por el modelo
            admissible_vars : set[str] 
                Set de atributos admitidos por el modelo
        """
        cls._db = db_collection
        cls._required_vars = required_vars
        cls._admissible_vars = admissible_vars
        # TODO
        if indexes is not None:
            for campo, tipo in indexes.items():
                if tipo=="unique":
                    cls._db.create_index([(campo, pymongo.ASCENDING)], unique=True)
                elif tipo=="asc":
                    cls._db.create_index([(campo, pymongo.ASCENDING)])   
                elif tipo=="geosphere":
                    cls._location_var=campo
                    cls._db.create_index([(campo + "_loc", pymongo.GEOSPHERE)])


        # Recorrer indexes y crear cada índice segun su tipo: 'unique', 'asc'
        # y 'geosphere'. Comparar el tipo por igualdad, no con el operador 'in'.
        # Ojo con el índice geoespacial: save() guarda el GeoJSON Point en
        # <campo>_loc, luego el índice 2dsphere va sobre <campo>_loc, mientras
        # que _location_var debe guardar el nombre del campo base.


class ModelCursor:
    """ 
    Cursor para iterar sobre los documentos del resultado de una
    consulta. Los documentos deben ser devueltos en forma de objetos
    modelo.

    Attributes
    ----------
        model_class : Model
            Clase para crear los modelos de los documentos que se iteran.
        cursor : pymongo.cursor.Cursor
            Cursor de pymongo a iterar

    Methods
    -------
        __iter__() -> Generator
            Devuelve un iterador que recorre los elementos del cursor
            y devuelve los documentos en forma de objetos modelo.
    """

    def __init__(self, model_class: Model, cursor: pymongo.cursor.Cursor):
       
        self.model = model_class
        self.cursor = cursor
    
    def __iter__(self) -> Generator:
        while self.cursor:#va a repetirse mientras que el cursor tenga mas documentos
         doc = next(self.cursor)# guardamos el diccionario del siguiente en doc
         yield self.model(**doc)# validamos y creamos el objeto, y con el yield como pide el enunciado el objeto al for iterado

def initApp(definitions_path: str = "./models.yml", mongodb_uri="mongodb://localhost:27017/", db_name="abd", scope=globals()) -> None:
    """ 
    Declara las clases que heredan de Model para cada uno de los 
    modelos de las colecciones definidas en definitions_path.
    Inicializa las clases de los modelos proporcionando los indices y 
    atributos admitidos y requeridos para cada una de ellas y la conexión a la
    collecion de la base de datos.
    
    Parameters
    ----------
        definitions_path : str
            ruta al fichero de definiciones de modelos
        mongodb_uri : str
            uri de conexion a la base de datos
        db_name : str
            nombre de la base de datos
    """
    #TODO
    # Inicializar base de datos
    client = MongoClient(mongodb_uri)
    db = client[db_name]
   
    
    with open(definitions_path, "r", encoding="utf-8") as f:
        definitions = yaml.safe_load(f)
        #or [] es para evitar un error si el models.yml tiene null
        for tipo, variable in definitions.items():
                indices = {}
                for campo in variable.get("unique_indexes") or []: 
                    indices[campo] = "unique"
                for campo in variable.get("regular_indexes") or []:
                    indices[campo] = "asc"
                if variable.get("location_index") or []:  
                    indices[variable["location_index"]] = "geosphere"
                cls = type(tipo, (Model,), {})
                scope[tipo] = cls
                cls.init_class(db_collection=db[tipo],indexes=indices,required_vars=set(variable.get("required_vars", [])),admissible_vars=set(variable.get("admissible_vars", [])),)
if __name__ == '__main__':
    
    # Inicializar base de datos y modelos con initApp
    #TODO
    initApp()#initApp funciona bien 

    #pruebas iniciales 
    r = Recinto(nombre="Wizink Center", aforo=15000, zonas=4, direccion="Avenida de Felipe II, s/n, Madrid")
    # r.save() insertar funciona bien

    print(f"Objeto guardado con ID: {r._data.get('_id')}")
    r.aforo = 17000

    print(f"Variables  para modificar: {r._modified_vars}")
    # r.save() actualizar funciona bien 
    # r.color_fachada = "Rojo" no se pueden insertar atributos no permitidos 
    
    
    
    # Hacer pruebas para comprobar que funciona correctamente el modelo
    #TODO
    # Crear modelo

    # Asignar nuevo valor a variable admitida del objeto 

    # Asignar nuevo valor a variable no admitida del objeto 

    # Guardar

    # Asignar nuevo valor a variable admitida del objeto

    # Guardar

    # Buscar nuevo documento con find

    # Obtener primer documento

    # Modificar valor de variable admitida

    # Guardar
