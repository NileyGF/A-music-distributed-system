# Spotify. A music distributed system.

## Autores:

- Niley González Ferrales C-411   [@NileyGF](https://github.com/NileyGF)
- Josué Rodríguez Ramírez C-412   [@josueRdgz](https://github.com/josueRdgz)

### Proyecto en github: https://github.com/NileyGF/A-music-distributed-system

## Introducción

## Ejecución

## Tipos de servidores: 
Concurrencia:

Servidores concurrentes un hilo (o proceso) espera
peticiones y ante cada petición, le pasa la petición a otro
hilo (o proceso).

Localización:

Punto de entrada desconocido resoluble mediante un
servicio de nombres (debe conocerse la ubicación del
servicio de nombres)

Control:

Sin control los clientes que quieren desconectarse,
simplemente abortan la conexión (Ej: terminando la propia
aplicación cliente)
Con control se establece un canal de comunicación
adicional entre cliente y servidor, de forma que el cliente
puede actuar sobre el servidor: para detenerlo, pararlo,
reanudarlo, etc.

Estado interno:

Sin estado los servidores no guardan información
respecto al estado de los clientes ni respecto a su
conversación

## Servidores de nombre

Ventajas

Se puede lograr una gran tolerancia a fallas (Ej: el envío del
comando ping para determinar si un cliente está disponible)

Desventajas

No es propicio para lograr un gran escalabilidad. Existe un
control centralizado, en los skeleton, de las referencias.

## Sincronización
cosas de reloj
## Elección
anillo

Se supone que los nodos están ordenados en una anillo
lógico (Ej: en orden creciente de identificadores).
2 Cuando un nodo quiere elegir nuevo líder envía
ELECCION por el anillo (al siguiente del anillo que esté
vivo que debe confirmar).
3 Cada nodo que recibe el mensaje incluye su propio ID en
el mensaje.
4 Cuando el mensaje llega de vuelta al iniciador contiene los
IDs de todos los nodos participantes. En este momento
envía un mensaje LIDER por el anillo avisando del nuevo
líder (el nodo mayor).
## Transacciones en la base de datos

## Replicación y consistencia

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