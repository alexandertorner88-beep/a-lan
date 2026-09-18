# Ligasajt — resultat från Simresults

En resultatsajt i Formel 1-stil som hämtar sina siffror direkt från Simresults.
Efter ett race lägger du till en rad i `races.json`. Resten sköter sig själv.

## Så här hänger det ihop

```
races.json   ──►  build.py  ──►  site/data.json  ──►  site/index.html
(du redigerar)   (hämtar CSV)    (byggs åt dig)      (sajten)
```

`build.py` hämtar `https://simresults.net/<id>/csv` för varje deltävling och
plockar ut kval, race 1, race 2 och alla incidenter. Bana och datum läses ur
filen, så du behöver inte skriva in dem.

## Sätt upp det (en gång, ca 15 minuter)

1. Skapa ett nytt repository på GitHub. Kalla det t.ex. `liga`.
   Sätt det till **Public** — annars kostar GitHub Pages pengar.
2. Ladda upp alla filer i den här mappen till repot, med samma struktur.
   Enklast via **Add file → Upload files** på GitHub, dra in hela mappen.
3. Gå till **Settings → Pages**. Under *Build and deployment*, välj
   **Source: GitHub Actions**. Spara.
4. Gå till fliken **Actions** och kör *Bygg och publicera ligasajten* med
   **Run workflow**. Efter ungefär en minut ligger sajten på
   `https://<ditt-användarnamn>.github.io/liga/`.

## Lägg till ett race

Öppna `races.json` på GitHub, klicka på pennan och lägg till en rad:

```json
{ "id": "260917-V98", "round": 1, "name": "Knutstorp" },
{ "id": "261015-A12", "round": 2, "name": "Anderstorp" }
```

`id` är koden i Simresults-adressen: `simresults.net/261015-A12` ger
`261015-A12`. `name` är valfritt — utan det används banans namn.

Spara ("Commit changes"), så byggs sajten om på någon minut. Ställningen i
förar- och märkesmästerskapet räknas om automatiskt.

Sajten byggs också om varje morgon, så om ett resultat rättas på Simresults
hämtas ändringen in av sig själv.

## Ändra poängsystemet

Överst i `races.json`:

```json
"points": {
  "table": [25, 18, 15, 12, 10, 8, 6, 4, 2, 1],
  "pole": 1,
  "fastest": 1
}
```

`table` är poäng för placering 1, 2, 3 och så vidare i **varje** race — kör ni
två race per kväll delas poängen ut två gånger. `pole` ges till den som vinner
kvalet, `fastest` till snabbaste varv i respektive race. Sätt till `0` för att
stänga av.

## Kör lokalt

```bash
python3 build.py
python3 -m http.server -d site 8000
```

Sajten ligger då på http://localhost:8000. Inga paket behöver installeras.

## Att tänka på

**Två förare med samma namn.** Ni har två som heter "Robin S". Sajten skiljer
dem åt på bilmärket i mästerskapstabellen, men incidentlistan från Simresults
innehåller bara namnet — alla deras incidentpoäng hamnar därför på samma förare.
Det löser sig bara genom att de får olika namn i spelet.

**Incidentpoängen räknas inte in i mästerskapet.** De visas per deltävling och
som en kolumn i förartabellen, men påverkar inte poängen. Vill ni ha avdrag går
det att lägga till.

**Om ett bygge misslyckas** står felet under fliken Actions. Vanligaste orsaken
är ett felstavat `id`. Deltävlingar som går att hämta byggs ändå, så sajten
ligger kvar och fungerar.
