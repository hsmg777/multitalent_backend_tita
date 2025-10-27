# app/services/personality/questions.py

# Estructura esperada por el portal:
# - code: "Q01".."Q26" (debe coincidir con SCORING_RULES)
# - text: enunciado
# - scale_type: "single_choice_4"
# - min_value / max_value: 1..4
# - order: posición
# - options: lista [{value: 1..4, label: "A. ..."}]

QUESTIONS = [
    {
        "code": "Q01",
        "text": "En un restaurante. Estoy esperando mesa, me dicen que faltan 10 minutos y pasan veinte:",
        "scale_type": "single_choice_4",
        "min_value": 1, "max_value": 4, "order": 1,
        "options": [
            {"value": 1, "label": "A. Me molesto y le digo al mesero que ya pasó el doble de tiempo, y le pregunto que si tardará mucho más me iré."},
            {"value": 2, "label": "B. No me doy cuenta, pues estoy metidísimo en la conversación."},
            {"value": 3, "label": "C. No me fijo o, aunque me dé cuenta, no digo algo."},
            {"value": 4, "label": "D. Le digo al mesero exactamente la hora en que llegué y exactamente el tiempo que ha pasado, le pido que por favor me diga con exactitud cuánto tiempo más falta para poder tomar una decisión."},
        ],
    },
    {
        "code": "Q02",
        "text": "Tengo mucha hambre y prisa. El mesero me trae un platillo que yo no pedí:",
        "scale_type": "single_choice_4",
        "min_value": 1, "max_value": 4, "order": 2,
        "options": [
            {"value": 1, "label": "A. Me molesto y le digo impositivamente si no estaba poniendo atención cuando ordené."},
            {"value": 2, "label": "B. Converso con el mesero para explicarle que no es lo que le pedí."},
            {"value": 3, "label": "C. Me quedo callado y me adapto a lo que me trajeron."},
            {"value": 4, "label": "D. Le digo de manera directa que eso no fue lo que pedí."},
        ],
    },
    {
        "code": "Q03",
        "text": "En una reunión de amigos:",
        "scale_type": "single_choice_4",
        "min_value": 1, "max_value": 4, "order": 3,
        "options": [
            {"value": 1, "label": "A. Me gusta convencer a los demás de mis opiniones y gozo hablar de cosas relacionadas con mi trabajo."},
            {"value": 2, "label": "B. Converso mucho o cuento chistes, hablo más de lo que escucho."},
            {"value": 3, "label": "C. Me quedo escuchando; la gente me busca porque soy excelente escucha pues pongo atención."},
            {"value": 4, "label": "D. Observo y analizo a la gente; si doy mi opinión, lo hago únicamente si conozco del tema, y será algo preciso."},
        ],
    },
    {
        "code": "Q04",
        "text": "Mis compañeros de trabajo me describirían como alguien:",
        "scale_type": "single_choice_4",
        "min_value": 1, "max_value": 4, "order": 4,
        "options": [
            {"value": 1, "label": "A. Energético, fuerte y agresivo."},
            {"value": 2, "label": "B. Social, alegre, platicador."},
            {"value": 3, "label": "C. Tranquilo, paciente, amable."},
            {"value": 4, "label": "D. Concreto, disciplinado, metódico."},
        ],
    },
    {
        "code": "Q05",
        "text": "En una discusión:",
        "scale_type": "single_choice_4",
        "min_value": 1, "max_value": 4, "order": 5,
        "options": [
            {"value": 1, "label": "A. Busco tener la razón y no me detengo hasta conseguirla; aparte me gusta discutir."},
            {"value": 2, "label": "B. Trato de decirles que no es para tanto, pues discutir me da flojera."},
            {"value": 3, "label": "C. Odio la agresión y mejor digo que sí, que estoy de acuerdo, con tal de no argumentar."},
            {"value": 4, "label": "D. Me baso en los hechos y busco comprobar mi punto de vista, para que esté bien fundamentado, y espero lo mismo de los demás."},
        ],
    },
    {
        "code": "Q06",
        "text": "Lo que realmente me emociona en la vida:",
        "scale_type": "single_choice_4",
        "min_value": 1, "max_value": 4, "order": 6,
        "options": [
            {"value": 1, "label": "A. Los retos, la novedad, arriesgar."},
            {"value": 2, "label": "B. Las sorpresas, la diversión, el juego."},
            {"value": 3, "label": "C. La dulzura, el cariño, aceptación."},
            {"value": 4, "label": "D. Aprender, sabiduría, el conocimiento."},
        ],
    },
    {
        "code": "Q07",
        "text": "Si alguien me agrede:",
        "scale_type": "single_choice_4",
        "min_value": 1, "max_value": 4, "order": 7,
        "options": [
            {"value": 1, "label": "A. Agredo de regreso pues necesito sacar mi enojo de inmediato; lo bueno es que así como se me sube de rápido, así también se me baja."},
            {"value": 2, "label": "B. Evado la situación, o me hago el loco."},
            {"value": 3, "label": "C. Me quedo callado y no demuestro lo que siento."},
            {"value": 4, "label": "D. Me angustio, me privo y me lo guardo, pero a la larga exploto; y cuando esto pasa, cuidado, pues no se me baja nada fácil."},
        ],
    },
    {
        "code": "Q08",
        "text": "Cuando voy de compras:",
        "scale_type": "single_choice_4",
        "min_value": 1, "max_value": 4, "order": 8,
        "options": [
            {"value": 1, "label": "A. Busco buenas ofertas, me encantan los descuentos."},
            {"value": 2, "label": "B. Me divierte ir de compras y me encanta comprar regalos; dicen que soy un comprador compulsivo."},
            {"value": 3, "label": "C. Soy indeciso; me cuesta mucho trabajo decidir y escoger."},
            {"value": 4, "label": "D. Sé lo que quiero y no gasto mi dinero si no lo encuentro; soy muy definido."},
        ],
    },
    {
        "code": "Q09",
        "text": "¿Qué frase te describe mejor?",
        "scale_type": "single_choice_4",
        "min_value": 1, "max_value": 4, "order": 9,
        "options": [
            {"value": 1, "label": "A. Soy activo y energético; me gusta hacer más de una cosa a la vez; la gente me pregunta si nunca me canso."},
            {"value": 2, "label": "B. Soy alegre y jovial; si veo a alguien triste busco ponerlo de buen humor; la gente me pregunta si nunca me deprimo."},
            {"value": 3, "label": "C. Soy tranquilo y pasivo; me gusta que la gente se lleve bien y que no haya agresión; la gente me pregunta si nunca me enojo."},
            {"value": 4, "label": "D. Soy analítico y observador; me gusta resolver problemas mentales y encontrar la solución; la gente me dice que soy muy responsable y aprensivo."},
        ],
    },
    {
        "code": "Q10",
        "text": "Cuando estoy trabajando en equipo soy:",
        "scale_type": "single_choice_4",
        "min_value": 1, "max_value": 4, "order": 10,
        "options": [
            {"value": 1, "label": "A. El que manda y organiza."},
            {"value": 2, "label": "B. El que anima para que todos pongan ganas."},
            {"value": 3, "label": "C. El que apoya para lograr un equipo unido."},
            {"value": 4, "label": "D. El que organiza la parte estratégica para lograr la mayor probabilidad de éxito."},
        ],
    },
    {
        "code": "Q11",
        "text": "Mis hermanos y la gente que me rodea, dicen que mis peores defectos son:",
        "scale_type": "single_choice_4",
        "min_value": 1, "max_value": 4, "order": 11,
        "options": [
            {"value": 1, "label": "A. Ser agresivo y visceral."},
            {"value": 2, "label": "B. Ser distraído y desorganizado."},
            {"value": 3, "label": "C. Ser pasivo y lento."},
            {"value": 4, "label": "D. Ser terco y cuadrado."},
        ],
    },
    {
        "code": "Q12",
        "text": "Algunas de mis cualidades son:",
        "scale_type": "single_choice_4",
        "min_value": 1, "max_value": 4, "order": 12,
        "options": [
            {"value": 1, "label": "A. Ser determinado y seguro."},
            {"value": 2, "label": "B. Ser optimista y alegre."},
            {"value": 3, "label": "C. Ser adaptado y pacífico."},
            {"value": 4, "label": "D. Ser cumplido y estable."},
        ],
    },
    {
        "code": "Q13",
        "text": "Estoy caminando, me tropiezo con algún desconocido:",
        "scale_type": "single_choice_4",
        "min_value": 1, "max_value": 4, "order": 13,
        "options": [
            {"value": 1, "label": "A. Espero a que se quite de mi camino para seguir adelante."},
            {"value": 2, "label": "B. Le sonrío y me sigo de frente."},
            {"value": 3, "label": "C. Le pido perdón y me sigo de frente."},
            {"value": 4, "label": "D. Me hago a un lado y sin hablar sigo mi camino."},
        ],
    },
    {
        "code": "Q14",
        "text": "En el trabajo, sobresalgo en:",
        "scale_type": "single_choice_4",
        "min_value": 1, "max_value": 4, "order": 14,
        "options": [
            {"value": 1, "label": "A. La toma de decisiones rápidas."},
            {"value": 2, "label": "B. Las relaciones públicas."},
            {"value": 3, "label": "C. La capacidad para adaptarme en equipos."},
            {"value": 4, "label": "D. La seguridad de tener calidad y puntualidad."},
        ],
    },
    {
        "code": "Q15",
        "text": "Mis defectos en el trabajo son:",
        "scale_type": "single_choice_4",
        "min_value": 1, "max_value": 4, "order": 15,
        "options": [
            {"value": 1, "label": "A. No me gusta que me digan qué hacer."},
            {"value": 2, "label": "B. Desordenado y olvidadizo, a veces impuntual."},
            {"value": 3, "label": "C. Trabajo mal bajo presión."},
            {"value": 4, "label": "D. No me gusta delegar; prefiero trabajar solo."},
        ],
    },
    {
        "code": "Q16",
        "text": "Mi madre dice que de chico yo era:",
        "scale_type": "single_choice_4",
        "min_value": 1, "max_value": 4, "order": 16,
        "options": [
            {"value": 1, "label": "A. Mandón y exigente."},
            {"value": 2, "label": "B. Alegre y conversador con todo el mundo."},
            {"value": 3, "label": "C. Obediente y tranquilo."},
            {"value": 4, "label": "D. Educado y no me gustaba ensuciarme."},
        ],
    },
    {
        "code": "Q17",
        "text": "Al expresarme:",
        "scale_type": "single_choice_4",
        "min_value": 1, "max_value": 4, "order": 17,
        "options": [
            {"value": 1, "label": "A. Digo las cosas como son."},
            {"value": 2, "label": "B. Las digo de manera indirecta para no lastimar."},
            {"value": 3, "label": "C. Casi no expreso lo que siento."},
            {"value": 4, "label": "D. Digo las cosas de manera diplomática."},
        ],
    },
    {
        "code": "Q18",
        "text": "La emoción que demuestro con más frecuencia es:",
        "scale_type": "single_choice_4",
        "min_value": 1, "max_value": 4, "order": 18,
        "options": [
            {"value": 1, "label": "A. Enojo."},
            {"value": 2, "label": "B. Optimismo."},
            {"value": 3, "label": "C. No demuestro emoción."},
            {"value": 4, "label": "D. Miedo."},
        ],
    },
    {
        "code": "Q19",
        "text": "Las maestras me reconocían porque:",
        "scale_type": "single_choice_4",
        "min_value": 1, "max_value": 4, "order": 19,
        "options": [
            {"value": 1, "label": "A. Discutía mucho, y me encantaba demostrar que todo lo sabía."},
            {"value": 2, "label": "B. Era muy amiguero y hablaba mucho."},
            {"value": 3, "label": "C. No interrumpía y era callado."},
            {"value": 4, "label": "D. Buen estudiante y muy analítico."},
        ],
    },
    {
        "code": "Q20",
        "text": "Características que más te describen:",
        "scale_type": "single_choice_4",
        "min_value": 1, "max_value": 4, "order": 20,
        "options": [
            {"value": 1, "label": "A. Autosuficiente y ambicioso."},
            {"value": 2, "label": "B. Despreocupado y popular."},
            {"value": 3, "label": "C. Cooperativo y adaptable."},
            {"value": 4, "label": "D. Preciso y exacto."},
        ],
    },
    {
        "code": "Q21",
        "text": "Características que más te describen:",
        "scale_type": "single_choice_4",
        "min_value": 1, "max_value": 4, "order": 21,
        "options": [
            {"value": 1, "label": "A. Valiente y osado."},
            {"value": 2, "label": "B. Amiguero y platicador."},
            {"value": 3, "label": "C. Tolerante y flexible."},
            {"value": 4, "label": "D. Reservado y respetuoso."},
        ],
    },
    {
        "code": "Q22",
        "text": "Características que más te describen:",
        "scale_type": "single_choice_4",
        "min_value": 1, "max_value": 4, "order": 22,
        "options": [
            {"value": 1, "label": "A. Obstinado, determinación para defenderme."},
            {"value": 2, "label": "B. Confiado, creo en los demás."},
            {"value": 3, "label": "C. Servicial, me gusta ayudar a los demás."},
            {"value": 4, "label": "D. Prudente, me gusta reflexionar bien las cosas."},
        ],
    },
    {
        "code": "Q23",
        "text": "Características que más te describen:",
        "scale_type": "single_choice_4",
        "min_value": 1, "max_value": 4, "order": 23,
        "options": [
            {"value": 1, "label": "A. Emprendedor, con fuerza de voluntad."},
            {"value": 2, "label": "B. Juguetón, atraigo a la gente."},
            {"value": 3, "label": "C. Generoso, me adapto a los demás."},
            {"value": 4, "label": "D. Cuidadoso, tengo tacto al decir las cosas."},
        ],
    },
    {
        "code": "Q24",
        "text": "Características que más te describen:",
        "scale_type": "single_choice_4",
        "min_value": 1, "max_value": 4, "order": 24,
        "options": [
            {"value": 1, "label": "A. Atrevido, cree en sí mismo."},
            {"value": 2, "label": "B. Cálido, motiva a los demás."},
            {"value": 3, "label": "C. Calmado, hace lo que le piden."},
            {"value": 4, "label": "D. Pulcro, ordenado y limpio."},
        ],
    },
    {
        "code": "Q25",
        "text": "Características que más te describen:",
        "scale_type": "single_choice_4",
        "min_value": 1, "max_value": 4, "order": 25,
        "options": [
            {"value": 1, "label": "A. Confrontador, me gusta argumentar."},
            {"value": 2, "label": "B. Animado, alma de la fiesta."},
            {"value": 3, "label": "C. Armonioso, abierto a sugerencias."},
            {"value": 4, "label": "D. Culto, busca tener conocimiento."},
        ],
    },
    {
        "code": "Q26",
        "text": "Características que más te describen:",
        "scale_type": "single_choice_4",
        "min_value": 1, "max_value": 4, "order": 26,
        "options": [
            {"value": 1, "label": "A. Tomo acción, persuasivo, convincente."},
            {"value": 2, "label": "B. Carismático, magnético, desinhibido."},
            {"value": 3, "label": "C. Humilde, compasivo con la gente."},
            {"value": 4, "label": "D. Sistemático, escéptico, precavido."},
        ],
    },
]
