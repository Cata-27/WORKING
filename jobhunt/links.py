"""Enlaces de búsqueda manual para portales sin API (Ana aplica desde su propia cuenta)."""

from __future__ import annotations

from urllib.parse import quote_plus, urlencode


def enlaces_del_dia(ciudad: str = "Barranquilla") -> list[dict]:
    q_dev = "desarrollador junior"
    linkedin = "https://www.linkedin.com/jobs/search/?" + urlencode({
        "keywords": "desarrollador OR developer OR practicante desarrollo",
        "location": "Colombia",
        "f_E": "1,2",          # prácticas + nivel de entrada
        "f_WT": "2,3",         # remoto + híbrido
        "f_TPR": "r86400",     # últimas 24 horas
        "sortBy": "DD",
    })
    linkedin_bq = "https://www.linkedin.com/jobs/search/?" + urlencode({
        "keywords": "desarrollador",
        "location": f"{ciudad}, Atlántico, Colombia",
        "f_E": "1,2",
        "f_TPR": "r604800",    # última semana
        "sortBy": "DD",
    })
    return [
        {"portal": "LinkedIn", "descripcion": "Remoto/híbrido, prácticas y junior, últimas 24 h", "url": linkedin},
        {"portal": "LinkedIn", "descripcion": f"En {ciudad}, última semana", "url": linkedin_bq},
        {"portal": "Computrabajo", "descripcion": f"Desarrollador en {ciudad}",
         "url": f"https://co.computrabajo.com/trabajo-de-desarrollador-en-{ciudad.lower()}"},
        {"portal": "Computrabajo", "descripcion": "Desarrollador junior remoto",
         "url": "https://co.computrabajo.com/trabajo-de-desarrollador-junior-remoto"},
        {"portal": "elempleo", "descripcion": "Desarrollador junior",
         "url": f"https://www.elempleo.com/co/ofertas-empleo/?Search={quote_plus(q_dev)}"},
        {"portal": "Magneto", "descripcion": "Desarrollador en Colombia",
         "url": f"https://www.magneto365.com/co/empleos?q={quote_plus('desarrollador')}"},
        {"portal": "Indeed", "descripcion": f"Desarrollador junior en {ciudad} o remoto",
         "url": "https://co.indeed.com/jobs?" + urlencode({"q": q_dev, "l": ciudad, "fromage": "3", "sort": "date"})},
        {"portal": "Wellfound (startups)", "descripcion": f"Startups en {ciudad}",
         "url": f"https://wellfound.com/location/{ciudad.lower()}"},
        {"portal": "Wellfound (startups)", "descripcion": "Startups en Colombia",
         "url": "https://wellfound.com/role/l/developer/colombia"},
        {"portal": "Y Combinator", "descripcion": "Startups YC contratando en Bogotá/Colombia",
         "url": "https://www.ycombinator.com/jobs/location/bogota"},
        {"portal": "Get on Board", "descripcion": "Programación, junior, remoto",
         "url": "https://www.getonbrd.com/empleos/programacion?remote=true&seniority=junior"},
    ]
