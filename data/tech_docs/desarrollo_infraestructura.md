# TalentoHub — Desarrollo e Infraestructura
Documento interno de Tecnología. Versión 3.3. Vigente desde mayo de 2026.

[Desarrollo] ¿Cómo obtengo acceso a los repositorios de código?
El acceso se otorga por equipo al ingresar, según el rol técnico definido en tu contratación. Los repositorios adicionales se solicitan por el catálogo con aprobación del dueño del repositorio.

[Desarrollo] ¿Cuál es el flujo de trabajo para subir código?
Cada cambio va en una rama propia derivada de la rama principal, con al menos una revisión aprobada antes de integrarse. Los cambios directos sobre la rama principal están bloqueados por política.

[Desarrollo] ¿Qué se revisa en un code review?
Se revisa correctitud, cobertura de pruebas, manejo de errores, ausencia de credenciales embebidas y adherencia a las guías de estilo del lenguaje. La revisión debe completarse dentro de un día hábil.

[Desarrollo] ¿Dónde guardo las credenciales de una aplicación?
En el gestor de secretos corporativo, nunca en el código ni en archivos de configuración versionados. El escaneo automático del repositorio bloquea cualquier commit que contenga credenciales detectables.

[Desarrollo] ¿Cómo pido un ambiente de pruebas?
Los ambientes de pruebas se aprovisionan desde la plataforma interna de autoservicio, indicando el proyecto y la duración estimada. Los ambientes sin uso durante 14 días se apagan automáticamente.

[Desarrollo] ¿Cuál es el proceso para un despliegue a producción?
Los despliegues requieren que pasen las pruebas automatizadas, aprobación del líder técnico y registro en el calendario de cambios. Hay ventana de congelamiento durante los cierres de mes.

[Infraestructura] ¿Qué es la ventana de mantenimiento?
Es el período programado para actualizaciones de infraestructura, los domingos entre las 2:00 y las 6:00. Durante ese lapso algunos servicios internos pueden estar intermitentes y se anuncia con 72 horas de anticipación.

[Infraestructura] ¿Cómo reporto una caída de un servicio productivo?
Usa el canal de escalamiento de incidentes, que activa al equipo de guardia sin importar la hora. Incluye qué servicio falla, desde cuándo, cuántos usuarios afecta y si hay mensaje de error visible.

[Infraestructura] ¿Qué es un postmortem y cuándo se hace?
Es el documento de análisis posterior a un incidente de severidad alta, con línea de tiempo, causa raíz y acciones correctivas. Se redacta dentro de los cinco días hábiles siguientes y no busca responsables individuales.

[Infraestructura] ¿Dónde consulto los logs de una aplicación?
En la plataforma centralizada de observabilidad, filtrando por servicio y rango de tiempo. El acceso se solicita por el catálogo y se otorga por equipo, con retención de 30 días.

[Datos] ¿Cómo pido acceso a la base de datos de producción?
El acceso directo a producción se otorga de forma excepcional y temporal, con aprobación del líder de datos y justificación documentada. Para consultas analíticas el canal correcto es la réplica de solo lectura.

[Datos] ¿Puedo exportar datos a una hoja de cálculo?
Las exportaciones de datos agregados están permitidas. Exportar datos personales de clientes requiere aprobación del área legal y queda registrado en la bitácora de auditoría.

[Datos] ¿Qué es la clasificación de la información?
Los datos se clasifican en públicos, internos, confidenciales y restringidos. Cada nivel define dónde puede almacenarse, con quién compartirse y por cuánto tiempo conservarse, según la política TI-160.

[Red] ¿Cómo me conecto al wifi de la oficina?
La red corporativa usa tus credenciales del dominio con certificado, y el equipo queda configurado en el aprovisionamiento inicial. La red de invitados tiene contraseña rotativa disponible en recepción.

[Red] ¿Puedo conectar dispositivos personales a la red corporativa?
Los dispositivos personales solo pueden usar la red de invitados. La red corporativa está reservada para equipos gestionados por TI con las políticas de seguridad aplicadas.

[Red] ¿Por qué algunos sitios web están bloqueados?
El filtrado de navegación bloquea categorías de riesgo y sitios asociados a malware o phishing. Si un sitio necesario para tu trabajo está bloqueado, solicita su habilitación por ticket con la justificación.

[Cuentas] ¿Qué pasa con mis accesos cuando cambio de área?
El cambio de área dispara una revisión de accesos: se retiran los permisos del rol anterior y se otorgan los del nuevo. Tu líder anterior confirma qué accesos deben revocarse.

[Cuentas] ¿Qué pasa con mi cuenta cuando salgo de la empresa?
La cuenta se deshabilita el último día laboral al cierre de la jornada. El buzón se conserva 60 días bajo custodia del líder del área y luego se elimina definitivamente.

[Cuentas] ¿Cómo delego acceso a mis archivos durante mis vacaciones?
Comparte las carpetas necesarias con tu respaldo desde el almacenamiento corporativo antes de salir. No se permite compartir credenciales personales bajo ninguna circunstancia.

[Cuentas] ¿Qué es la revisión periódica de accesos?
Cada trimestre los líderes revisan y certifican los accesos de su equipo. Los accesos no certificados se revocan automáticamente al cierre del ciclo de revisión.
