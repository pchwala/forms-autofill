# Strategia Generowania Odpowiedzi — Ankieta Sharentingowa

## 1. Pytania formularza (schemat JSON)

Pełna definicja pytań znajduje się w `form_config.json`. Poniżej skrót z nazwami opcji,
które MUSZĄ być użyte w odpowiedziach (dokładne dopasowanie ciągów znaków jest wymagane).

| ID | Treść skrócona | Typ | Opcje |
|----|----------------|-----|-------|
| Q1 | Płeć | radio | Kobieta / Mężczyzna |
| Q2 | Wiek | radio | 18-25 / 26-35 / 36-45 / 46-55 / 56 lub więcej |
| Q3 | Wykształcenie | radio | Podstawowe / Zasadnicze zawodowe / branżowe / Średnie / Wyższe |
| Q4 | Miejsce zamieszkania | radio | Wieś / Miasto poniżej 100 tys. mieszkańców / Miasto powyżej 100 tys. mieszkańców |
| Q5 | Częstość publikowania w SM | radio | Nigdy / Rzadko / Czasami / Często / Bardzo często |
| Q6 | Status rodzicielski | radio | Opcja 1 - Jestem rodzicem lub opiekunem przynajmniej jednego dziecka, które nie ukończyło jeszcze 18. roku życia / Opcja 2 - Jestem osobą planującą potomstwo / Opcja 3 - Żadne z powyższych |
| Q7 | Liczba dzieci do 18 lat | radio | 1 / 2 / 3 / 4 / 5 lub więcej |
| Q8 | Wiek dzieci | checkbox | 0-2 lata / 3-6 lat / 7-10 lat / 11-14 lat / 15-17 lat |
| Q9 | Wizerunek = dane biometryczne | radio | Zdecydowanie nie / Raczej nie / Trudno powiedzieć / Raczej tak / Zdecydowanie tak |
| Q10 | Algorytmy / metadane / trwałość w sieci | radio | (j.w.) |
| Q11 | Bezp. inform. = prawo do intymności | radio | (j.w.) |
| Q12 | Czytanie warunków korzystania | radio | (j.w.) |
| Q13 | Znajomość RODO | radio | (j.w.) |
| Q14 | Znajomość digital kidnapping | radio | (j.w.) |
| Q15 | Ryzyko deepfake / AI — realne | radio | (j.w.) |
| Q16 | Użycie zdjęć przez osoby trzecie — prawdopodobne | radio | (j.w.) |
| Q17 | Ryzyko hejtu rówieśniczego | radio | (j.w.) |
| Q18 | Każde zdjęcie buduje cyfrowy ślad | radio | (j.w.) |
| Q19 | Pytam dziecko o zgodę | radio | (j.w.) |
| Q20 | Ogranicz grono odbiorców | radio | (j.w.) |
| Q21 | Techniczne metody ochrony (blur/emoji) | radio | (j.w.) |
| Q22 | Brak real-time lokalizacji | radio | (j.w.) |
| Q23 | Aktywnie poszerzam wiedzę | radio | (j.w.) |
| Q24 | Budowa SM zachęca do publikowania | radio | (j.w.) |
| Q25 | Skomplikowane ustawienia prywatności zniechęcają | radio | (j.w.) |
| Q26 | Analizuję dobro dziecka vs autopromocja | radio | (j.w.) |
| Q27 | Potrzeba natychmiastowego relacjonowania sukcesów | radio | (j.w.) |
| Q28 | Mogę spędzać czas z dzieckiem bez telefonu | radio | (j.w.) |

### Kluczowy routing Q6
```
Q6 = Opcja 1 (rodzic)       → next_page → Q7, Q8, Q9–Q28 MUSZĄ być wypełnione
Q6 = Opcja 2 (planuje)      → blok_I   → Q7 = null, Q8 = null; Q9–Q28 MUSZĄ być wypełnione
Q6 = Opcja 3 (żadne)        → end       → Q7–Q28 WSZYSTKIE null / nieobecne
```

---

## 2. Podstawy badawcze

Rozkład odpowiedzi oparty jest na następujących weryfikowalnych źródłach:

### Statystyki globalne / europejskie

| Źródło | Wynik | Zastosowanie |
|--------|-------|--------------|
| **AVG Technologies Survey** | 92% dwulatków w USA ma jakąś formę obecności w internecie | Baseline sharentingu; skala zjawiska |
| **Kopecky et al. 2020** *(Children and Youth Services Review)* | 70–80% rodziców w Czechach i Hiszpanii uczestniczy w sharentingu | Najbliższe polskiemu kontekstowi dane CE; motywuje wysoki poziom sharentingu u Person A i B |
| **Research Now** (UK, FR, DE, IT) | ~75% rodziców zadeklarowało chęć udostępniania zdjęć niemowląt | Powszechność zjawiska w Europie Zachodniej |
| **Fisher-Price Australia** | 90% australijskich rodziców przyznało się do over-sharingu | Globalny zasięg zjawiska |
| **University of Michigan C.S. Mott Children's Hospital** | 75% rodziców zna kogoś, kto nadmiernie udostępnia dane dziecka; ponad 50% samych rodziców udostępniło krępujące treści; 27% — treści potencjalnie nieodpowiednie | Niski poziom Q19 (zgoda dziecka), Q21 (ochrona techniczna) |
| **Barclays Bank (2018)** | Oszustwa internetowe wobec młodych będą kosztować £670 mln do 2030; 2/3 przypadków powiązanych ze sharentingiem | Motywuje niski poziom Q14 (digital kidnapping) wśród przeciętnych rodziców |
| **OECD iLibrary — Digital Parenting and the Datafied Child** | 70% brytyjskich nastolatków twierdzi, że rodzice nie szanują ich tożsamości cyfrowej; 40% czuło się zakłopotanych postami rodziców | Rozbieżność zgody (Q19); motywuje realistyczną rzadkość pytania dziecka |
| **Pew Research Center (2015) — Parents and Social Media** | 72% rodziców uważa SM za przydatne dla więzi emocjonalnej; 74% otrzymuje wsparcie parentingowe przez SM | Q24 (SM zachęca do publikowania), Q27 (potrzeba walidacji) |
| **Steinberg, Stacey (2016)** *(Emory Law Journal)* | Dzieci rzadko dają zgodę i często proszą o usunięcie postów, które rodzice ignorują | Q19 (zgoda dziecka) — niska praktyka |

### Kontekst polski

| Źródło | Wynik | Zastosowanie |
|--------|-------|--------------|
| **Anna Brosch (2016)** *(The New Educational Review)* | Polskie badanie sharentingu na Facebooku — dokumentuje zjawisko i jego ryzyka w Polsce | Polish-specific validity |
| **GUS — Rocznik Demograficzny 2023** | Średni wiek urodzenia pierwszego dziecka: ~29 lat (kobiety), ~31 lat (mężczyźni); ~40% Polaków mieszka na wsi lub w małych miastach | Rozkład Q2 dla Opcji 1; rozkład Q4 |
| **Eurostat Digital Economy 2023 (Polska)** | Polska poniżej średniej UE w zakresie kompetencji cyfrowych i świadomości bezpieczeństwa | Uzasadnienie niskich wyników Q9, Q10, Q13, Q14 |
| **RODO (rozporządzenie UE 2016/679) — art. 8** | Zgoda osoby sprawującej władzę rodzicielską wymagana dla dzieci poniżej 16 lat; większość rodziców nieświadoma konsekwencji | Niski poziom Q13 (RODO), Q9 (dane biometryczne) |
| **CERT Polska — Raport 2023** | Phishing = 64,5% wszystkich incydentów; niski poziom świadomości cyfrowej wśród ogółu społeczeństwa | Ogólna niska kompetencja cyfrowa; Q10, Q12 |

### Kluczowe korelacje behawioralne

- **Wykształcenie a świadomość**: Wyższe wykształcenie koreluje z lepszą znajomością RODO (Q13), algorytmów (Q10) i pojęcia digital kidnapping (Q14).
- **Miejsce zamieszkania**: Rodzice ze wsi i małych miast wykazują niższe kompetencje cyfrowe i rzadziej stosują środki ochronne (Q19–Q23).
- **Płeć**: Kobiety nieco częściej stosują zachowania ochronne (Q19–Q22) i głębiej analizują motywacje (Q26); mężczyźni nieco częściej wykazują impulsywność (Q27).
- **Aktywność w SM (Q5)**: Wyższa częstość korzystania z SM → większa zgoda z Q24 (SM zachęca do publikowania) i Q25 (ustawienia zniechęcają).
- **Refleksja (Q26) a impulsywność (Q27)**: Silna negatywna korelacja — osoby analizujące dobro dziecka rzadko odczuwają natychmiastową potrzebę dzielenia się.
- **Świadomość cyfrowego śladu (Q18) a zachowania ochronne**: Wysoki Q18 → wyższe Q19, Q20, Q21, Q22.

---

## 3. Plan rozkładu agregacyjnego (100 odpowiedzi)

### Skew Q6 (cel główny: 80% rodzice lub planujący)

| Q6 | Opcja | Liczba | % |
|----|-------|--------|---|
| Opcja 1 — rodzic dziecka <18 lat | 80 | 80% |
| Opcja 2 — planuje potomstwo | 10 | 10% |
| Opcja 3 — żadne z powyższych | 10 | 10% |

### Dane demograficzne (wszystkie 100 odpowiedzi)

| Q1 Płeć | Liczba | Q2 Wiek | Liczba |
|---------|--------|---------|--------|
| Kobieta | 55 | 18-25 | 15 |
| Mężczyzna | 45 | 26-35 | 32 |
| | | 36-45 | 32 |
| | | 46-55 | 16 |
| | | 56 lub więcej | 5 |

| Q3 Wykształcenie | Liczba | Q4 Zamieszkanie | Liczba |
|-----------------|--------|-----------------|--------|
| Podstawowe | 5 | Wieś | 25 |
| Zasadnicze zawodowe / branżowe | 18 | Miasto poniżej 100 tys. mieszkańców | 32 |
| Średnie | 35 | Miasto powyżej 100 tys. mieszkańców | 43 |
| Wyższe | 42 | | |

| Q5 Częstość publikowania | Liczba |
|--------------------------|--------|
| Nigdy | 8 |
| Rzadko | 17 |
| Czasami | 30 |
| Często | 28 |
| Bardzo często | 17 |

### Dzieci (tylko Opcja 1, n=80)

| Q7 Liczba dzieci | Liczba |
|-----------------|--------|
| 1 | 29 |
| 2 | 37 |
| 3 | 11 |
| 4 | 3 |
| 5 lub więcej | 0 |

| Q8 Wiek dzieci *(checkbox, suma > 80)* | Liczba zaznaczeń |
|----------------------------------------|-----------------|
| 0-2 lata | 24 |
| 3-6 lat | 33 |
| 7-10 lat | 29 |
| 11-14 lat | 24 |
| 15-17 lat | 16 |

### Rozkład odpowiedzi Q9–Q28 (tylko Opcja 1 + Opcja 2, n=90)

#### Blok I — Pojęcie bezpieczeństwa informacyjnego

| Pytanie | Zd. nie | Raczej nie | Trudno | Raczej tak | Zd. tak |
|---------|---------|------------|--------|------------|---------|
| **Q9** Wizerunek = dane biometryczne | 27 | 27 | 18 | 13 | 5 |
| **Q10** Algorytmy / metadane / trwałość | 25 | 29 | 20 | 12 | 4 |
| **Q11** Bezp. inform. = prawo do intymności | 5 | 9 | 18 | 36 | 22 |
| **Q12** Czytanie warunków korzystania | 25 | 27 | 18 | 16 | 4 |
| **Q13** Znajomość RODO | 20 | 25 | 25 | 16 | 4 |

> Q9 mean ≈ 2.2 (niska świadomość techniczna). Q11 mean ≈ 3.7 (intuicyjne rozumienie prawa do intymności jest wyższe).

#### Blok II — Zagrożenia związane ze sharentingiem

| Pytanie | Zd. nie | Raczej nie | Trudno | Raczej tak | Zd. tak |
|---------|---------|------------|--------|------------|---------|
| **Q14** Znajomość digital kidnapping | 34 | 25 | 16 | 11 | 4 |
| **Q15** Ryzyko AI / deepfake — realne | 5 | 11 | 23 | 36 | 15 |
| **Q16** Użycie zdjęć przez 3. strony — prawdopodobne | 5 | 13 | 20 | 36 | 16 |
| **Q17** Ryzyko hejtu rówieśniczego | 7 | 16 | 25 | 31 | 11 |
| **Q18** Każde zdjęcie buduje cyfrowy ślad | 5 | 7 | 16 | 36 | 26 |

> Q14 mean ≈ 2.1 (pojęcie bardzo mało znane). Q18 mean ≈ 3.9 (wysoka świadomość cyfrowego śladu — szeroko relacjonowane w mediach).

#### Blok III — Działania prewencyjne

| Pytanie | Zd. nie | Raczej nie | Trudno | Raczej tak | Zd. tak |
|---------|---------|------------|--------|------------|---------|
| **Q19** Pytam dziecko o zgodę | 22 | 23 | 13 | 23 | 9 |
| **Q20** Ograniczam grono odbiorców | 9 | 13 | 11 | 34 | 23 |
| **Q21** Techniczne metody ochrony (blur/emoji) | 27 | 27 | 16 | 16 | 4 |
| **Q22** Brak real-time lokalizacji | 5 | 9 | 16 | 31 | 29 |
| **Q23** Aktywnie poszerzam wiedzę | 20 | 25 | 20 | 18 | 7 |

> Q21 mean ≈ 2.2 (techniczne metody ochrony stosuje bardzo mała część rodziców). Q22 mean ≈ 3.9 (świadomość zagrożeń lokalizacyjnych wyższa — szeroko omawiana w kampaniach społecznych).

#### Blok IV — Czynniki wpływające na świadomość

| Pytanie | Zd. nie | Raczej nie | Trudno | Raczej tak | Zd. tak |
|---------|---------|------------|--------|------------|---------|
| **Q24** SM zachęca do publikowania zdjęć dzieci | 7 | 9 | 20 | 34 | 20 |
| **Q25** Ustawienia prywatności zniechęcają | 5 | 11 | 18 | 34 | 22 |
| **Q26** Analizuję dobro dziecka vs autopromocja | 11 | 18 | 20 | 29 | 12 |
| **Q27** Potrzeba natychmiastowego relacjonowania | 25 | 27 | 16 | 16 | 6 |
| **Q28** Czas z dzieckiem bez odruchowego telefonu | 7 | 11 | 16 | 34 | 22 |

> Q24 mean ≈ 3.6 (większość dostrzega mechanizmy angażowania platform). Q27 mean ≈ 2.4 (większość nie przyznaje się do impulsywnego dzielenia — efekt społecznej pożądaności).

---

## 4. Archetypy person

Zamiast 100 losowych odpowiedzi, generowane są 5 odrębnych person. Każda ma stały wzorzec
odpowiedzi z lekką wariancją, by uniknąć identycznych duplikatów.

---

### Persona A — "Świadoma Mama Miejska"
**Liczba: 12 odpowiedzi (12K)**

| Atrybut | Wartość |
|---------|---------|
| Q1 Płeć | Kobieta (12) |
| Q2 Wiek | 26-35 (8) / 36-45 (4) |
| Q3 Wykształcenie | Wyższe (12) |
| Q4 Zamieszkanie | Miasto powyżej 100 tys. mieszkańców (12) |
| Q5 Częstość SM | Często (6) / Czasami (4) / Bardzo często (2) |
| Q6 Status | Opcja 1 — Jestem rodzicem (12) |
| Q7 Dzieci | 1 (6) / 2 (6) |
| Q8 Wiek dzieci | 0-2 lata: 4 zaznaczeń / 3-6 lat: 6 / 7-10 lat: 4 / 11-14 lat: 2 |
| Q9 Biometryka | Raczej tak (6) / Zdecydowanie tak (4) / Trudno powiedzieć (2) |
| Q10 Algorytmy | Raczej tak (5) / Zdecydowanie tak (3) / Trudno powiedzieć (4) |
| Q11 Intymność | Zdecydowanie tak (8) / Raczej tak (4) |
| Q12 Warunki | Raczej tak (5) / Trudno powiedzieć (4) / Raczej nie (3) |
| Q13 RODO | Raczej tak (6) / Zdecydowanie tak (3) / Trudno powiedzieć (3) |
| Q14 Dig. kidnapping | Raczej tak (5) / Zdecydowanie tak (4) / Trudno powiedzieć (3) |
| Q15 AI/deepfake | Zdecydowanie tak (7) / Raczej tak (5) |
| Q16 3. strony | Raczej tak (6) / Zdecydowanie tak (6) |
| Q17 Hejt | Raczej tak (7) / Zdecydowanie tak (3) / Trudno powiedzieć (2) |
| Q18 Cyfrowy ślad | Zdecydowanie tak (8) / Raczej tak (4) |
| Q19 Zgoda dziecka | Raczej tak (6) / Zdecydowanie tak (4) / Trudno powiedzieć (2) |
| Q20 Grono odbiorców | Zdecydowanie tak (6) / Raczej tak (6) |
| Q21 Blur/emoji | Raczej tak (5) / Zdecydowanie tak (4) / Trudno powiedzieć (3) |
| Q22 Lokalizacja | Zdecydowanie tak (8) / Raczej tak (4) |
| Q23 Wiedza | Raczej tak (6) / Zdecydowanie tak (3) / Trudno powiedzieć (3) |
| Q24 SM zachęca | Raczej tak (6) / Zdecydowanie tak (4) / Trudno powiedzieć (2) |
| Q25 Ustawienia | Raczej tak (6) / Zdecydowanie tak (4) / Trudno powiedzieć (2) |
| Q26 Refleksja | Zdecydowanie tak (6) / Raczej tak (5) / Trudno powiedzieć (1) |
| Q27 Impulsywność | Zdecydowanie nie (8) / Raczej nie (4) |
| Q28 Czas bez tel. | Zdecydowanie tak (6) / Raczej tak (6) |

**Uzasadnienie**: Młode i średniego wieku wykształcone matki mieszkające w dużych miastach.
Aktywne w SM, ale świadome ryzyk. Czytały o digital kidnapping i deepfake'ach. Konsekwentnie
stosują metody ochrony (pytają dzieci o zgodę, ograniczają odbiorców, nie publikują lokalizacji).
Silnie refleksyjne (Q26), nisko impulsywne (Q27). Wkład: 12/100 odpowiedzi = 12%.

---

### Persona B — "Przeciętny Rodzic"
**Liczba: 30 odpowiedzi (15K / 15M)**

| Atrybut | Wartość |
|---------|---------|
| Q1 Płeć | Kobieta (15) / Mężczyzna (15) |
| Q2 Wiek | 26-35 (12) / 36-45 (12) / 18-25 (4) / 46-55 (2) |
| Q3 Wykształcenie | Wyższe (12) / Średnie (15) / Zasadnicze zawodowe / branżowe (3) |
| Q4 Zamieszkanie | Miasto powyżej 100 tys. mieszkańców (12) / Miasto poniżej 100 tys. mieszkańców (12) / Wieś (6) |
| Q5 Częstość SM | Czasami (12) / Rzadko (10) / Często (8) |
| Q6 Status | Opcja 1 — Jestem rodzicem (30) |
| Q7 Dzieci | 1 (10) / 2 (16) / 3 (4) |
| Q8 Wiek dzieci | Mieszane — patrz reguły spójności |
| Q9 Biometryka | Raczej nie (10) / Trudno powiedzieć (10) / Raczej tak (6) / Zdecydowanie nie (4) |
| Q10 Algorytmy | Raczej nie (12) / Trudno powiedzieć (10) / Zdecydowanie nie (5) / Raczej tak (3) |
| Q11 Intymność | Raczej tak (14) / Trudno powiedzieć (8) / Zdecydowanie tak (5) / Raczej nie (3) |
| Q12 Warunki | Raczej nie (10) / Zdecydowanie nie (8) / Trudno powiedzieć (8) / Raczej tak (4) |
| Q13 RODO | Trudno powiedzieć (12) / Raczej nie (10) / Raczej tak (5) / Zdecydowanie nie (3) |
| Q14 Dig. kidnapping | Zdecydowanie nie (10) / Raczej nie (10) / Trudno powiedzieć (7) / Raczej tak (3) |
| Q15 AI/deepfake | Raczej tak (13) / Trudno powiedzieć (9) / Zdecydowanie tak (5) / Raczej nie (3) |
| Q16 3. strony | Raczej tak (13) / Trudno powiedzieć (8) / Zdecydowanie tak (5) / Raczej nie (4) |
| Q17 Hejt | Trudno powiedzieć (10) / Raczej tak (12) / Raczej nie (5) / Zdecydowanie tak (3) |
| Q18 Cyfrowy ślad | Raczej tak (13) / Zdecydowanie tak (9) / Trudno powiedzieć (5) / Raczej nie (3) |
| Q19 Zgoda dziecka | Raczej nie (10) / Trudno powiedzieć (8) / Raczej tak (8) / Zdecydowanie nie (4) |
| Q20 Grono odbiorców | Raczej tak (13) / Zdecydowanie tak (8) / Raczej nie (5) / Trudno powiedzieć (4) |
| Q21 Blur/emoji | Zdecydowanie nie (10) / Raczej nie (10) / Trudno powiedzieć (6) / Raczej tak (4) |
| Q22 Lokalizacja | Raczej tak (12) / Zdecydowanie tak (10) / Trudno powiedzieć (5) / Raczej nie (3) |
| Q23 Wiedza | Raczej nie (10) / Trudno powiedzieć (9) / Zdecydowanie nie (6) / Raczej tak (5) |
| Q24 SM zachęca | Raczej tak (13) / Trudno powiedzieć (8) / Zdecydowanie tak (6) / Raczej nie (3) |
| Q25 Ustawienia | Raczej tak (12) / Trudno powiedzieć (8) / Zdecydowanie tak (7) / Raczej nie (3) |
| Q26 Refleksja | Raczej tak (12) / Trudno powiedzieć (8) / Raczej nie (6) / Zdecydowanie tak (4) |
| Q27 Impulsywność | Raczej nie (12) / Zdecydowanie nie (9) / Trudno powiedzieć (6) / Raczej tak (3) |
| Q28 Czas bez tel. | Raczej tak (13) / Zdecydowanie tak (8) / Trudno powiedzieć (6) / Raczej nie (3) |

**Uzasadnienie**: Najliczniejsza persona — odzwierciedla przeciętnego polskiego rodzica aktywnego
cyfrowo. Zna ryzyko cyfrowego śladu (Q18) i deepfake'ów (Q15), ale pojęcia biometryczne (Q9)
i digital kidnapping (Q14) są mu w dużej mierze obce. Stosuje częściową ochronę: ogranicza
odbiorców (Q20), nie udostępnia lokalizacji (Q22), ale rzadko pyta dziecko o zgodę (Q19)
i prawie nie stosuje technicznej ochrony twarzy (Q21). Wkład: 30/100 = 30%.

---

### Persona C — "Mało Świadomy Rodzic"
**Liczba: 18 odpowiedzi (10M / 8K)**

| Atrybut | Wartość |
|---------|---------|
| Q1 Płeć | Mężczyzna (10) / Kobieta (8) |
| Q2 Wiek | 36-45 (10) / 46-55 (6) / 26-35 (2) |
| Q3 Wykształcenie | Zasadnicze zawodowe / branżowe (8) / Podstawowe (4) / Średnie (6) |
| Q4 Zamieszkanie | Wieś (10) / Miasto poniżej 100 tys. mieszkańców (8) |
| Q5 Częstość SM | Rzadko (8) / Nigdy (4) / Czasami (6) |
| Q6 Status | Opcja 1 — Jestem rodzicem (18) |
| Q7 Dzieci | 2 (8) / 3 (6) / 1 (4) |
| Q8 Wiek dzieci | Starsze dzieci: 7-10 lat: 8 / 11-14 lat: 8 / 15-17 lat: 7 / 3-6 lat: 4 |
| Q9 Biometryka | Zdecydowanie nie (9) / Raczej nie (7) / Trudno powiedzieć (2) |
| Q10 Algorytmy | Zdecydowanie nie (10) / Raczej nie (6) / Trudno powiedzieć (2) |
| Q11 Intymność | Trudno powiedzieć (6) / Raczej tak (6) / Raczej nie (4) / Zdecydowanie nie (2) |
| Q12 Warunki | Zdecydowanie nie (8) / Raczej nie (7) / Trudno powiedzieć (3) |
| Q13 RODO | Zdecydowanie nie (7) / Raczej nie (7) / Trudno powiedzieć (4) |
| Q14 Dig. kidnapping | Zdecydowanie nie (12) / Raczej nie (5) / Trudno powiedzieć (1) |
| Q15 AI/deepfake | Trudno powiedzieć (6) / Raczej nie (5) / Raczej tak (5) / Zdecydowanie nie (2) |
| Q16 3. strony | Raczej nie (6) / Trudno powiedzieć (5) / Raczej tak (5) / Zdecydowanie nie (2) |
| Q17 Hejt | Trudno powiedzieć (7) / Raczej nie (5) / Raczej tak (4) / Zdecydowanie nie (2) |
| Q18 Cyfrowy ślad | Trudno powiedzieć (6) / Raczej tak (6) / Raczej nie (4) / Zdecydowanie nie (2) |
| Q19 Zgoda dziecka | Zdecydowanie nie (8) / Raczej nie (7) / Trudno powiedzieć (3) |
| Q20 Grono odbiorców | Zdecydowanie nie (6) / Raczej nie (6) / Trudno powiedzieć (4) / Raczej tak (2) |
| Q21 Blur/emoji | Zdecydowanie nie (10) / Raczej nie (6) / Trudno powiedzieć (2) |
| Q22 Lokalizacja | Raczej tak (6) / Trudno powiedzieć (5) / Raczej nie (4) / Zdecydowanie nie (3) |
| Q23 Wiedza | Zdecydowanie nie (8) / Raczej nie (8) / Trudno powiedzieć (2) |
| Q24 SM zachęca | Trudno powiedzieć (8) / Raczej nie (5) / Raczej tak (5) |
| Q25 Ustawienia | Raczej tak (7) / Trudno powiedzieć (6) / Zdecydowanie tak (3) / Raczej nie (2) |
| Q26 Refleksja | Zdecydowanie nie (6) / Raczej nie (6) / Trudno powiedzieć (6) |
| Q27 Impulsywność | Raczej tak (7) / Trudno powiedzieć (5) / Zdecydowanie tak (4) / Raczej nie (2) |
| Q28 Czas bez tel. | Raczej nie (7) / Trudno powiedzieć (5) / Zdecydowanie nie (4) / Raczej tak (2) |

**Uzasadnienie**: Starsi rodzice z obszarów wiejskich i małomiejskich, niższe wykształcenie,
rzadka aktywność w SM. Nieznajomość pojęć technicznych (biometryka, digital kidnapping,
algorytmy) jest prawie totalna. Nie stosują żadnych środków ochrony. Wyraźnie impulsywni
(Q27) i mają trudność z ograniczeniem czasu na telefonie (Q28). Wkład: 18/100 = 18%.

---

### Persona D — "Przyszły Rodzic"
**Liczba: 20 odpowiedzi (10K / 10M)**

| Atrybut | Wartość |
|---------|---------|
| Q1 Płeć | Kobieta (10) / Mężczyzna (10) |
| Q2 Wiek | 18-25 (10) / 26-35 (8) / 36-45 (2) |
| Q3 Wykształcenie | Wyższe (10) / Średnie (8) / Zasadnicze zawodowe / branżowe (2) |
| Q4 Zamieszkanie | Miasto powyżej 100 tys. mieszkańców (10) / Miasto poniżej 100 tys. mieszkańców (6) / Wieś (4) |
| Q5 Częstość SM | Często (8) / Bardzo często (6) / Czasami (4) / Rzadko (2) |
| Q6 Status | Opcja 2 — Jestem osobą planującą potomstwo (20) |
| Q7 | **null** (niedotyczy — brak dzieci) |
| Q8 | **null** (niedotyczy — brak dzieci) |
| Q9 Biometryka | Trudno powiedzieć (8) / Raczej nie (6) / Raczej tak (4) / Zdecydowanie nie (2) |
| Q10 Algorytmy | Raczej nie (8) / Trudno powiedzieć (7) / Raczej tak (4) / Zdecydowanie nie (1) |
| Q11 Intymność | Raczej tak (9) / Zdecydowanie tak (6) / Trudno powiedzieć (5) |
| Q12 Warunki | Raczej nie (8) / Zdecydowanie nie (6) / Trudno powiedzieć (4) / Raczej tak (2) |
| Q13 RODO | Trudno powiedzieć (8) / Raczej nie (7) / Raczej tak (4) / Zdecydowanie nie (1) |
| Q14 Dig. kidnapping | Zdecydowanie nie (8) / Raczej nie (7) / Trudno powiedzieć (5) |
| Q15 AI/deepfake | Raczej tak (9) / Zdecydowanie tak (6) / Trudno powiedzieć (5) |
| Q16 3. strony | Raczej tak (9) / Zdecydowanie tak (5) / Trudno powiedzieć (6) |
| Q17 Hejt | Raczej tak (8) / Trudno powiedzieć (7) / Zdecydowanie tak (3) / Raczej nie (2) |
| Q18 Cyfrowy ślad | Zdecydowanie tak (9) / Raczej tak (8) / Trudno powiedzieć (3) |
| Q19 Zgoda dziecka | Raczej tak (8) / Zdecydowanie tak (5) / Trudno powiedzieć (5) / Raczej nie (2) |
| Q20 Grono odbiorców | Raczej tak (9) / Zdecydowanie tak (6) / Trudno powiedzieć (5) |
| Q21 Blur/emoji | Trudno powiedzieć (7) / Raczej tak (6) / Raczej nie (5) / Zdecydowanie nie (2) |
| Q22 Lokalizacja | Zdecydowanie tak (9) / Raczej tak (8) / Trudno powiedzieć (3) |
| Q23 Wiedza | Trudno powiedzieć (8) / Raczej nie (6) / Raczej tak (4) / Zdecydowanie nie (2) |
| Q24 SM zachęca | Zdecydowanie tak (8) / Raczej tak (8) / Trudno powiedzieć (4) |
| Q25 Ustawienia | Zdecydowanie tak (8) / Raczej tak (8) / Trudno powiedzieć (4) |
| Q26 Refleksja | Raczej tak (9) / Zdecydowanie tak (6) / Trudno powiedzieć (5) |
| Q27 Impulsywność | Zdecydowanie nie (9) / Raczej nie (8) / Trudno powiedzieć (3) |
| Q28 Czas bez tel. | Raczej tak (9) / Zdecydowanie tak (6) / Trudno powiedzieć (5) |

**Uzasadnienie**: Młodsi respondenci, aktywnie korzystający z SM, bez dzieci. Ich wiedza jest
bardziej teoretyczna — dobrze rozumieją ryzyko deepfake'ów (Q15), cyfrowego śladu (Q18)
i mechanizmy SM (Q24, Q25), ale mają niższe kompetencje w zakresie pojęć technicznych
(Q9, Q10) i RODO (Q13). Deklarują intencje ochronne (Q19, Q20, Q22), choć brak
praktycznego doświadczenia. Silnie dostrzegają wpływ designu SM (Q24, Q25 — wysoki).
Wkład: 20/100 = 20%.

---

### Persona E — "Niebędący Rodzicem"
**Liczba: 20 odpowiedzi (10K / 10M)**

| Atrybut | Wartość |
|---------|---------|
| Q1 Płeć | Kobieta (10) / Mężczyzna (10) |
| Q2 Wiek | 18-25 (5) / 26-35 (5) / 36-45 (4) / 46-55 (4) / 56 lub więcej (2) |
| Q3 Wykształcenie | Wyższe (8) / Średnie (8) / Zasadnicze zawodowe / branżowe (3) / Podstawowe (1) |
| Q4 Zamieszkanie | Miasto powyżej 100 tys. mieszkańców (8) / Miasto poniżej 100 tys. mieszkańców (7) / Wieś (5) |
| Q5 Częstość SM | Często (5) / Czasami (6) / Rzadko (5) / Nigdy (4) |
| Q6 Status | **Opcja 3 - Żadne z powyższych** (20) |
| Q7 | **null** — ankieta kończy się po Q6 |
| Q8 | **null** — ankieta kończy się po Q6 |
| Q9–Q28 | **null** — ankieta kończy się po Q6 (routing "end") |

**Uzasadnienie**: 20% respondentów to osoby bez dzieci i nieplanujące potomstwa — np. osoby
starsze, których dzieci są już dorosłe, lub osoby świadomie bezdzietne. Wchodzą na ankietę,
lecz zostają odfiltrowane przez Q6. Ich obecność nadaje wynikom naturalny rozkład
demograficzny. Wkład: 20/100 = 20%.

---

## 5. Reguły spójności (enforced per response)

### Reguły twarde (bez wyjątków)

1. **Routing Q6 — bezwzględny:**
   - `Q6 = "Opcja 3 - Żadne z powyższych"` → Q7, Q8, Q9–Q28 muszą być `null` lub nieobecne.
   - `Q6 = "Opcja 2 - Jestem osobą planującą potomstwo"` → Q7 i Q8 muszą być `null`; Q9–Q28 muszą być wypełnione.
   - `Q6 = "Opcja 1 - Jestem rodzicem lub opiekunem…"` → Q7, Q8, Q9–Q28 muszą być wypełnione.

2. **Q8 jako checkbox:**
   - Q8 musi być tablicą JSON (`["…"]`) z co najmniej jednym elementem (gdy wymagane).
   - `len(Q8) ≤ Q7_numeric` — liczba zaznaczonych przedziałów wiekowych nie może przekraczać liczby dzieci.

3. **Spójność wieku rodzica (Q2) z wiekiem dzieci (Q8):**
   - Q2 = `18-25` → Q8 zawiera wyłącznie `"0-2 lata"` lub `"3-6 lat"`.
   - Q2 = `26-35` → Q8 może zawierać `"0-2 lata"`, `"3-6 lat"` lub `"7-10 lat"`.
   - Q2 = `36-45` → Q8 może zawierać dowolny przedział.
   - Q2 = `46-55` → Q8 to głównie `"11-14 lat"` lub `"15-17 lat"`; dopuszczone `"7-10 lat"`.
   - Q2 = `56 lub więcej` → Q8 wyłącznie `"15-17 lat"`.

4. **Opcje muszą być dokładnym dopasowaniem** ciągów znaków z sekcji §1. Żadnych parafraz ani skrótów.

### Reguły miękkie (prawdopodobieństwa, nie bezwzględne)

| Warunek | Wpływ |
|---------|-------|
| Q3 = Wyższe | Q9, Q10, Q13, Q14 — przesunięcie w stronę „Raczej tak" / „Zdecydowanie tak" |
| Q3 = Podstawowe / Zasadnicze | Q9–Q14 — przesunięcie w stronę „Zdecydowanie nie" / „Raczej nie" |
| Q4 = Wieś | Niższe wyniki świadomości (Q9–Q18); rzadsze zachowania ochronne (Q19–Q23) |
| Q1 = Kobieta | Nieco wyższe Q19–Q22 (zachowania ochronne); wyższe Q26 (refleksja) |
| Q5 = Nigdy / Rzadko | Niższe Q24 i Q25 (mniejsza ekspozycja na mechanizmy SM) |
| Q5 = Często / Bardzo często | Wyższe Q24, Q25; możliwy wyższy Q27 |
| Q26 = Zdecydowanie tak | Q27 powinno być niskie (Zdecydowanie nie / Raczej nie) — negatywna korelacja |
| Q18 = Raczej tak / Zdecydowanie tak | Q19, Q20, Q21, Q22 powinny być wyższe (ochronne) |
| Q10 = Zdecydowanie nie | Q9 powinno być Zdecydowanie nie lub Raczej nie (brak wiedzy technicznej) |
| Q14 = Zdecydowanie tak | Q22 powinno być Raczej tak / Zdecydowanie tak (chroni lokalizację) |
| Persona D (Q6 = Opcja 2) | Q24, Q25 wyższe niż u Persona B przy tych samych danych demograficznych |
