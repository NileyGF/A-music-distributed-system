# Spotify. A music distributed system.

## Autores:

- Niley González Ferrales C-411   [@NileyGF](https://github.com/NileyGF)
- Josué Rodríguez Ramírez C-412   [@josueRdgz](https://github.com/josueRdgz)

### Proyecto en github: https://github.com/NileyGF/A-music-distributed-system

## Introducción

Presentamos el diseño de un sistema distribuido compuesto por cuatro tipos distintos de nodos, cada uno con una responsabilidad (role) específica. Nuestra arquitectura consiste de un servidor DNS encargado de resolver nombres de hosts en direcciones IP, servidores de datos almacenando y gestionando la música, servidores de enrutamiento encargados de atender a los clientes y redirigirlos, balanceadamente, a los servidores que proveen los archivos multimedia y los nodos clientes accediendo a los recursos del sistema. 

Nuestro sistema garantiza su funcionamiento si hay al menos un nodo de cada role. Sin embargo, si en esas condiciones se conectan muchos clientes es posible que el rendimiento no sea el mejor. 

## Ejecución

## Roles del sistema:
- **DNS**: implementamos este role para resolver dinámicamente la entrada al sistema tanto desde los clientes como desde otros servidores. Tiene tres funciones principales: agregar registros, resolución de nombre y mantenimiento de consistencia.

La adición de registros implica asociar un dominio con su dirección y un TTL (tiempo de vida), que indica el tiempo que debe durar ese registro en el DNS.

La resolución de nombre permite obtener todas las direcciones IP de los nodos activos en el sistema que corresponden al dominio solicitado.

Finalmente, la función de mantenimiento de consistencia conlleva a que cuando se inicia un nodo DNS se crea un subproceso que revisa periódicamente todos los registros almacenados para determinar si han expirado. Si es así, se contacta con el servidor correspondiente para comprobar su estado y, si responde correctamente, se renueva el TTL. Además, asegura que la dirección devuelta sea válida en el momento de la consulta.

- **Client**: este rol se encarga de manejar las solicitudes del usuario y comunicarse con el sistema de servidores distribuidos según sea necesario. Sus dos tareas principales incluyen actualizar la lista de metadatos de la música y solicitar canciones específicas al sistema para almacenarlas en cache y reproducirlas para el usuario.

- **Router**: su papel principal es manejar las solicitudes de los clientes, proporcionándoles información actualizada sobre listas de canciones y, dada una canción que el cliente desee, localizar los proveedores activos que ofrezcan la canción solicitada y enviar sus direcciones al cliente. Todo ello mientras intenta mantener balance en el sistema con estrategias estocásticas.

- **Data**: el role de manejo de datos fue implementado como un nodo que utiliza SQLite para almacenar las canciones como fragmentos cortos (por ejemplo, 10 segundos) en una base de datos dividida en dos tablas: una para los tags musicales y otra para la multimedia en sí misma. Está diseñado para manejar cuatro tipos de solicitudes: mostrar la lista de canciones disponibles, confirmar si puede ofrecer una canción específica, entregar un fragmento específico a partir de un tiempo en milisegundos, y suministrar varios fragmentos a partir de un tiempo determinado. 

De esta forma garantizamos que puede proveer todos los fragmento de una canción, los fragmentos a partir de un tiempo t, o solo un fragmento específico. Esta estrategia se desarrolló como medida de tolerancia a fallos y para mejorar la velocidad general del sistema, permitiendo al cliente empezar a reproducir la canción sin tener que esperar hasta que se haya descargado completamente.

## Asignación de roles dinámicamente

Los servidores de datos y routers conforman un anillo para garantizar la disponibilidad del sistema. En esta estructura, cuando se une un nuevo servidor comprueba que role es más necesario en ese momento y se asigna dinámicamente. Para ello contacta con el DNS para consultar cuantos servidores hay activos por cada role e intenta mantener una relación de 2:3 de servidores de data y servidores routers. 

En este anillo, cada integrante tiene una referencia a los 2 nodos que hay hacia adelante, y la referencia a su antecesor. Cuando un nuevo servidor llega, contacta con algún participante en el anillo y le pide unirse. Ese a su vez le proporciona sus referencias hacia adelante y actualiza al recién llegado como su nuevo sucesor. 

Además todos los nodos, al unirse al anillo crean un subproceso de supervisión para monitorear la consistencia del anillo y enviar informes periódicos a su sucesor. Si un servidor se desconecta y es detectado por este mecanismo, se envía un mensaje de alerta por todo el anillo y cada nodo incluye su información en el mensaje al reenviarlo. Cuando el mensaje vuelve al que detectó la falla (que se convierte en un Manager temporal), se contabilizan la cantidad de nodos en el anillo de cada role. Si se alcanza el mínimo en alguno, se envía un mensaje de Desbalance por el anillo, explicando que role es necesario. Cuando el primer servidor con el role opuesto al necesario recibe el mensaje, cambia de role para mantener la disponibilidad y funcionalidad del sistema distribuidado.

## Características generales de los servidores: 

- **Concurrencia**: Los servidores tienen la capacidad de manejar varias solicitudes simultáneamente. Al ser creados y establecer su role, designan un proceso que espera solicitudes y ante la llegada de una petición se crea otro proceso que se encarga de manejarla.

- **Localización**: El punto de entrada para las conexiones es desconocido y se resuelve mediante un servicio de nombres (lo que implica que todos conozcan la dirección del DNS).

- **Control**: Hay un canal de comunicación claramente definido entre los servidores y los usuarios, y los usuarios esperan una respuesta antes de volver a intentar comunicarse. Si reciben una respuesta, deben enviar un "acknowledgement" (ACK) para confirmar que han recibido la información correctamente.

- **Estado interno**: Los servidores carecen de información interna relacionada con el estado de los usuarios o conversaciones previas. Por tanto, no almacenan información personalizada sobre los usuarios.

## Servidor de nombre (DNS)
El nodo de DNS gestiona registros de tipo A. Un registro A posee los siguientes campos: label (nombre del recurso, en nuestro caso el dominio `dispotify.data`, `dispotify.router`, etc ); tipo (tipo de información, en nuestro caso A, que significa IPv4); clase (usualmente omitida ya que se utiliza solo `IN`); TTL (time to live, cantidad de tiempo que debe ser guardado el registro) y datos (datos reales del registro, osea, dirección: (IP, puerto) ).

Al inicializarce una instancia se crea un diccionario de 'headers' que por cada solicitud que puede recibir tiene como valor la función que la maneja. También empieza un subproceso para actualizar los registros basándose en sus valores de TTL.

## Coordinación
Decidimos implementar una arquitectura descentralizada de anillo sin líder (explicada anteriormente). Dónde cualquiera puede insertar nuevos nodos al anillo y puede ejercer de Manager temporal si detecta una desconexión. Esta decisión está encaminada a no crear puntos de fallas extras ya que la existencia de un líder añade seguridad y robustez al sistema si y solo si el líder no se cae, porque en esos casos surge un nuevo problema. 

## Transacciones en la base de datos
Los nodos de acceso a datos utilizan operaciones de transacción al acceder y modificar la base de datos. 
## Replicación y consistencia
## Balance de cargas
## Tolerancia a fallas
La tolerancia a fallas está fuertemente relacionada con los
Sistemas Dependientes. La dependencia cubre un conjunto de
requerimientos donde se incluyen los siguientes:
Disponibilidad
Confiabilidad
Seguridad
Mantenibilidad

un
sistema altamente disponible es aquel se encuentra trabajando
en cualquier instante de tiempo.

la confiabilidad está definida en términos de
intervalos de tiempo en ves de instantes de tiempo. Un sistema
altamente confiable es aquel que puede funcionar sin
interrupción por largos períodos de tiempo.

Seguridad
Esta propiedad se refiere a la posibilidad de un sistema de que
a pesar de fallar temporalmente en su correcto funcionamiento
no genera situaciones catastróficas.

Mantenibilidad
Se refiere a la facilidad con que un sistema con fallas puede
ser reparado. Un sistema altamente mantenible puede ser un
sistema con un alto grado de disponibilidad sobre todo si las
fallas pueden ser detectadas y reparadas automáticamente.

Tipos de fallas
Fallas Ocasionales: Ocurren una vez y luego desaparecen
Fallas Intermitentes: Ocurren, luego desaparecen por sí
solas, después reaparecen y así sucesivamente.
Fallas Permannentes: es una que continúa existiendo
hasta que el componente defectuoso es remplazado.

Enmascaramiento por redundancia
Si un sistema es Tolerante a Fallas debe ocultar la ocurrencia
de fallas en un proceso al resto de los procesos del sistema. La
técnica clave para enmascarar las fallas es utilizar la
redundancia. Esta puede puede ser de tres formas:
Redundancia de información
Redundancia de tiempo
Redundancia física

Redundancia de información
Se añade información extra para cuando pueda ocurrir un error
en la recepción de la información esta se pueda recuperar.
Redundancia de tiempo
Una acción es realizada y luego, si es necesario, se puede
volver a realizar. Esta redundancia es bastante útil frente a
fallas ocasionales o intermitentes.
Redundancia física
Equipamiento o procesos extras son adicionados de forma que
el sistema, como sistema, pueda tolerar la pérdida o el
malfuncionamiento de algunos componentes. Esta redundancia
se puede realizar a nivel de hardware o de software.

Grupos
La principal aproximación para tolerar la falla de procesos es
organizar varios procesos idénticos en grupos. Cuando un
mensaje es enviado al grupo todos los miembros del mismo lo
reciben. De esta manera esta forma si un proceso falla otro
puede ocupar su lugar.
Características
Los grupos deben ser dinámicos.
Se debe poder crear nuevos grupos y destruir los que no
se necesiten.
Un proceso se puede unir o abandonar cualquier grupo.
Un proceos puede formar parte de varios grupos.

Grupos Planos
Los grupos planos son simétricos y no tienen puntos de falla.
Si un proceso falla el grupo tiene un integrante menos pero
puede continuar su funcionamiento a no ser que quede sin
miembros. Tiene como desventaja la toma de decisiones.

Comunicación Punto a Punto
La comunicación punto a punto que se establece en los
sistemas distribuidos se suele realizar a partir de conexiones
TCP. Este protocolo posee sus propios mecanismos de
tolerancia a fallas y son transparentes a los clientes que lo
utilizan. Sin embargo en muchos casos el conexión TCP se
puede cerrar abruptamente producto de una falla externa a la
conexión. La única posibilidad de enmascarar esta falla es que
el sistema automáticamente detecte la falla de la conexión y
automáticamente cree una nueva conexión.

Fallas en RPC 
1 El cliente no puede localizar el servidor.
2 El request del cliente al servidor se pierde.
3 El servidor falla después de recibir el request.
4 El mensaje de respuesta del cliente al servidor se pierde.
5 El cliente falla después de enviar el request.

## Seguridad