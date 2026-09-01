var FORM_TITLE = 'Reklama w mediach społecznościowych w branży beauty';
var FORM_DESCRIPTION = 'Szanowni Państwo,\n\njestem studentką studiów magisterskich i zapraszam do udziału w anonimowym badaniu dotyczącym wpływu reklam w mediach społecznościowych na decyzje zakupowe w branży beauty.\n\nWypełnienie kwestionariusza jest w pełni dobrowolne i zajmie około 5 minut, a wyniki zostaną wykorzystane wyłącznie w celach naukowych.';

function buildBeautySocialMediaSurvey() {
  var form = FormApp.create(FORM_TITLE);
  form.setDescription(FORM_DESCRIPTION);
  form.setCollectEmail(false);
  form.setProgressBar(true);
  form.setAllowResponseEdits(false);
  form.setShowLinkToRespondAgain(false);
  form.setConfirmationMessage('Dziękuję za wypełnienie ankiety.');

  addMultipleChoice(form, 'Ile czasu średnio spędzasz dziennie w mediach społecznościowych?', [
    'Mniej niż godzinę',
    '1–2 godziny',
    '2–4 godziny',
    'Powyżej 4 godzin'
  ]);

  addCheckbox(form, 'Z jakich platform społecznościowych korzystasz regularnie w celu poszukiwania inspiracji lub informacji o produktach kosmetycznych?', [
    'Instagram',
    'TikTok',
    'YouTube',
    'Facebook',
    'Pinterest'
  ], 'Można wybrać kilka odpowiedzi', true);

  addGrid(form, 'Jak często korzystasz z poszczególnych platform społecznościowych w celu poszukiwania inspiracji lub informacji o produktach kosmetycznych?', [
    'Instagram',
    'TikTok',
    'Youtube',
    'Facebook',
    'Pinterest'
  ], ['1', '2', '3', '4', '5'], 'Skala częstotliwości:\n1 – Nigdy\n2 – Rzadziej niż raz w tygodniu\n3 – 1-2 razy w tygodniu\n4 – Kilka razy w tygodniu\n5 – Codziennie / Wielokrotnie w ciągu dnia');

  addMultipleChoiceWithOther(form, 'Jaki styl aktywności najlepiej opisuje Twoje codzienne korzystanie z social mediów?', [
    'Głównie przeglądam posty, zdjęcia i wideo przygotowane przez innych (np. tutoriale makijażowe, recenzje)',
    'Przeglądam treści, ale też aktywnie na nie reaguję (zostawiam polubienia, piszę komentarze, udostępniam dalej)',
    'Regularnie publikuję własne materiały, zdjęcia, recenzje lub makijaże'
  ]);

  addGrid(form, 'Jak często dokonujesz zakupu produktów z poszczególnych kategorii branży beauty pod wpływem reklam w mediach społecznościowych?', [
    'Kosmetyki do makijażu (np. podkłady, korektory, róże, palety cieni, pomadki)',
    'Kosmetyki do pielęgnacji twarzy (np. sera, kremy z filtrem SPF, toniki, pianki oczyszczające, kosmetyki po goleniu, do pielęgnacji brody)',
    'Kosmetyki do pielęgnacji i stylizacji włosów (np. odżywki, maski, wcierki, oleje, pomady, pasty do stylizacji włosów)',
    'Perfumy i zapachy',
    'Produkty do pielęgnacji ciała, dłoni i paznokci'
  ], ['1', '2', '3', '4', '5'], 'Skala częstotliwości:\n1 – Nigdy\n2 – Rzadko (raz na pół roku lub rzadziej)\n3 – Czasem (raz na 2-3 miesiące)\n4 – Często (raz w miesiącu)\n5 – Bardzo często (kilka razy w miesiącu)');

  addGrid(form, 'Jakie znaczenie mają dla Ciebie poniższe czynniki przy zakupie kosmetyków pod wpływem reklam w mediach społecznościowych?', [
    'Atrakcyjna cena / promocje',
    'Właściwości funkcjonalne (np. wysoka pigmentacja, mocne krycie, trwałość)',
    'Dobry i bezpieczny skład (np. składniki aktywne, kosmetyki wegańskie/naturalne)',
    'Estetyka i innowacyjność opakowania (np. unikalny design, system typu "blind box", wygodny aplikator)',
    'Rekomendacje znanej osoby / influencera',
    'Marka'
  ], ['1', '2', '3', '4', '5'], '(Skala: 1 – zupełnie bez znaczenia, 5 – bardzo duże znaczenie)');

  addMultipleChoice(form, 'Gdzie najczęściej finalizujesz zakup kosmetyku, który zainteresował Cię w mediach społecznościowych?', [
    'Przez Internet (sklep online marki, drogeria internetowa)',
    'Stacjonarnie (np. Rossmann, Hebe, Sephora, Douglas) po wcześniejszym obejrzeniu reklamy w sieci',
    'Jest mi to obojętne / zależy od dostępności promocji'
  ]);

  addMultipleChoice(form, 'W której fazie zakupu kosmetyków reklama w social mediach wywiera na Ciebie największy wpływ?', [
    'Uświadomienie potrzeby: Dowiaduję się o istnieniu nowego kosmetyku lub nowego trendu makijażowego/pielęgnacyjnego, którego wcześniej nie znałem/am',
    'Poszukiwanie informacji: Reklama dostarcza mi wiedzy o właściwościach, odcieniach, działaniu lub cenie konkretnego produktu',
    'Ocena alternatyw: Reklama przekonuje mnie, dlaczego dany kosmetyk jest lepszy od propozycji innych, konkurencyjnych marek',
    'Decyzja o zakupie: Reklama (np. z kodem rabatowym od influencera) skłania mnie do sfinalizowania transakcji w sklepie online'
  ]);

  addGrid(form, 'W jakim stopniu poniższe formaty i działania reklamowe w mediach społecznościowych przekonują Cię do zakupu produktów beauty?', [
    'Krótkie wideo (np. TikToki, Reelsy)',
    'Recenzje produktów na YouTube (dłuższe wideo)',
    'Zdjęcia "przed i po"',
    'Transmisje na żywo (live streams) z prezentacją produktów',
    'Posty sponsorowane z kodami rabatowymi'
  ], ['1', '2', '3', '4', '5'], 'Skala oceny:\n1 – W żadnym stopniu\n2 – W małym stopniu\n3 – W średnim stopniu\n4 – W dużym stopniu\n5 – W bardzo dużym stopniu');

  addMultipleChoice(form, 'Na której platformie reklamy i prezentacje kosmetyków uważasz za najbardziej przekonujące?', [
    'Instagram: ze względu na dopracowane estetycznie zdjęcia, swatche (próbki kolorów) na skórze oraz tutoriale w Reels/Stories',
    'TikTok: ze względu na dynamiczne, autentyczne i krótkie testy wideo (np. testy krycia lub trwałości "na żywo")',
    'YouTube: ze względu na długie, wyczerpujące recenzje, zestawienia ulubieńców miesiąca i testy kosmetyków przez cały dzień',
    'Facebook: ze względu na posty z linkami do sklepów oraz opinie na grupach dyskusyjnych'
  ]);

  addGrid(form, 'W jakim stopniu zgadzasz się z poniższymi stwierdzeniami dotyczącymi wpływu mediów społecznościowych na zachowania współczesnych konsumentów w branży beauty?', [
    'Reklamy w mediach społecznościowych są dla klientów głównym źródłem informacji o nowościach kosmetycznych.',
    'Opinie i rekomendacje influencerów (np. beauty vloggerów) mają duże znaczenie w decyzjach zakupowych klientów.',
    'Treści promocyjne na Instagramie są bardziej wiarygodne dla odbiorców niż te na Facebooku.',
    'Kupujący, widząc reklamę kosmetyku w mediach społecznościowych, zazwyczaj od razu szukają opinii innych użytkowników.',
    'Reklamy w mediach społecznościowych często skłaniają klientów do spontanicznego (nieplanowanego) zakupu kosmetyków.'
  ], ['1', '2', '3', '4', '5'], 'Skala oceny:\n1 – Zdecydowanie się nie zgadzam\n2 – Raczej się nie zgadzam\n3 – Nie mam zdania (Ani się zgadzam, ani się nie zgadzam)\n4 – Raczej się zgadzam\n5 – Zdecydowanie się zgadzam');

  addMultipleChoice(form, 'Jakie działanie marek kosmetycznych w social mediach najbardziej buduje Twoje pozytywne nastawienie i zaufanie do marki?', [
    'Pokazywanie autentyczności – reklamy prezentujące kosmetyki na prawdziwej, naturalnej skórze, bez użycia filtrów upiększających',
    'Promowanie wartości społecznych i etycznych (np. wspieranie zdrowia psychicznego, nietestowanie na zwierzętach – cruelty-free, ekologiczne opakowania)',
    'Współpraca z mikro-influencerami, którzy mają mniejsze zasięgi, ale tworzą bardzo naturalne, codzienne recenzje',
    'Oferowanie innowacyjnych, unikalnych formuł i rozwiązań produktowych'
  ]);

  addMultipleChoice(form, 'W jakim stopniu ufasz rekomendacjom produktów beauty formułowanym przez influencerów w ramach współprac sponsorowanych/płatnych reklam?', [
    'Zdecydowanie ufam – uważam, że polecają tylko sprawdzone produkty',
    'Raczej ufam, ale staram się zachować zdrowy rozsądek',
    'Mam ograniczone zaufanie – obawiam się, że ze względu na kontrakt wyolbrzymiają zalety kosmetyku',
    'Zdecydowanie nie ufam – traktuję to wyłącznie jako czysty komunikat sprzedażowy'
  ]);

  addCheckbox(form, 'Co irytuje Cię lub zniechęca w reklamach branży beauty w social mediach?', [
    'Gdy ten sam kosmetyk jest nachalnie promowany w tym samym czasie przez kilkunastu różnych twórców',
    'Trudność w odróżnieniu, co jest szczerą i bezpłatną opinią, a co ukrytą reklamą sponsorowaną',
    'Gdy produkt w rzeczywistości ma znacznie słabsze właściwości (np. słabsza pigmentacja, gorsze krycie, mniejsza trwałość) niż na wyidealizowanym filmie/zdjęciu',
    'Mówienie przy każdej reklamie, że dany produkt to „odkrycie roku”, jest niezastąpiony i że „już nigdy nie kupi się niczego innego”',
    'Używanie filtrów wygładzających lub upiększających podczas prezentowania efektów działania kosmetyków'
  ], 'Możesz zaznaczyć więcej niż jedną odpowiedź', true);

  addMultipleChoice(form, 'Czy zdarzyło Ci się zrezygnować z zakupu reklamowanego kosmetyku po przeczytaniu negatywnych komentarzy lub opinii innych użytkowników pod postem marki bądź influencera?', [
    'Tak, wielokrotnie – opinie innych konsumentów są dla mnie ważniejsze niż reklama',
    'Tak, ale rzadko – tylko w przypadku bardzo drogich produktów lub kosmetyków do pielęgnacji twarzy',
    'Nie, nigdy – wolę przetestować produkt samodzielnie'
  ]);

  addMultipleChoice(form, 'Czy fakt, że post jest oznaczony jako \'Współpraca płatna\' lub \'Reklama\', zmniejsza Twoje zaufanie do rekomendacji produktu?', [
    'Tak, zawsze',
    'Raczej tak',
    'To zależy od influencera/marki',
    'Raczej nie',
    'Nie, nie ma to wpływu na moje zaufanie'
  ]);

  addText(form, 'Proszę podać przykładową markę kosmetyczną, której reklamy w mediach społecznościowych uważasz za najbardziej skuteczne lub godne zaufania.');

  addMultipleChoice(form, 'Płeć:', [
    'Kobieta',
    'Mężczyzna',
    'Inna / Nie chcę podawać'
  ]);

  addMultipleChoice(form, 'Wiek:', [
    '18 - 24 lata',
    '25 - 34 lata',
    '35 - 44 lata',
    '45 - 54 lata',
    '55 lat i więcej'
  ]);

  addMultipleChoice(form, 'Miejsce zamieszkania:', [
    'Wieś',
    'Miasto do 50 tys. mieszkańców',
    'Miasto od 50 tys. do 150 tys. mieszkańców',
    'Miasto powyżej 150 tys. mieszkańców'
  ]);

  addMultipleChoice(form, 'Status zawodowy:', [
    'Uczeń / Student',
    'Osoba pracująca',
    'Osoba studiująca i pracująca',
    'Osoba niepracująca'
  ]);

  addMultipleChoice(form, 'Wykształcenie:', [
    'Podstawowe',
    'Zawodowe',
    'Średnie',
    'Wyższe'
  ]);

  addMultipleChoice(form, 'Ocena sytuacji materialnej:', [
    'Bardzo dobra',
    'Dobra',
    'Dostateczna',
    'Zła',
    'Bardzo zła'
  ]);

  return form;
}

function addMultipleChoice(form, title, choices) {
  var item = form.addMultipleChoiceItem();
  item.setTitle(title);
  item.setChoiceValues(choices);
  item.setRequired(true);
  return item;
}

function addMultipleChoiceWithOther(form, title, choices) {
  var item = addMultipleChoice(form, title, choices);
  item.showOtherOption(true);
  return item;
}

function addCheckbox(form, title, choices, helpText, allowOther) {
  var item = form.addCheckboxItem();
  item.setTitle(title);
  item.setChoiceValues(choices);
  item.setRequired(true);
  if (helpText) {
    item.setHelpText(helpText);
  }
  if (allowOther) {
    item.showOtherOption(true);
  }
  return item;
}

function addGrid(form, title, rows, columns, helpText) {
  var item = form.addGridItem();
  item.setTitle(title);
  item.setRows(rows);
  item.setColumns(columns);
  item.setRequired(true);
  if (helpText) {
    item.setHelpText(helpText);
  }
  return item;
}

function addText(form, title) {
  var item = form.addTextItem();
  item.setTitle(title);
  item.setRequired(true);
  return item;
}
