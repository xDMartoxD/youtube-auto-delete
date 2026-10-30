"""Demo data for providers that are not integrated with the real service yet."""

from src.domain.providers import ProviderType

# (title, artist, album, duration_ms)
CATALOG: list[tuple[str, str, str, int]] = [
    ("Blinding Lights", "The Weeknd", "After Hours", 200040),
    ("Levitating", "Dua Lipa", "Future Nostalgia", 203064),
    ("As It Was", "Harry Styles", "Harry's House", 167303),
    ("Bad Habit", "Steve Lacy", "Gemini Rights", 232066),
    ("Anti-Hero", "Taylor Swift", "Midnights", 200690),
    ("Flowers", "Miley Cyrus", "Endless Summer Vacation", 200455),
    ("Kill Bill", "SZA", "SOS", 153946),
    ("Cruel Summer", "Taylor Swift", "Lover", 178426),
    ("Heat Waves", "Glass Animals", "Dreamland", 238805),
    ("Stay", "The Kid LAROI & Justin Bieber", "F*CK LOVE 3", 141805),
    ("Good 4 U", "Olivia Rodrigo", "SOUR", 178147),
    ("Peaches", "Justin Bieber", "Justice", 198082),
    ("Watermelon Sugar", "Harry Styles", "Fine Line", 174000),
    ("Dance Monkey", "Tones And I", "The Kids Are Coming", 209438),
    ("Shape of You", "Ed Sheeran", "÷", 233712),
    ("Someone You Loved", "Lewis Capaldi", "Divinely Uninspired", 182160),
    ("Sunflower", "Post Malone & Swae Lee", "Spider-Verse", 158040),
    ("Circles", "Post Malone", "Hollywood's Bleeding", 215280),
    ("Bohemian Rhapsody", "Queen", "A Night at the Opera", 354320),
    ("Mr. Brightside", "The Killers", "Hot Fuss", 222200),
    ("Take On Me", "a-ha", "Hunting High and Low", 225280),
    ("Dreams", "Fleetwood Mac", "Rumours", 257800),
    ("Everybody Wants to Rule the World", "Tears for Fears", "Songs from the Big Chair", 251480),
    ("Africa", "TOTO", "Toto IV", 295893),
    ("Smells Like Teen Spirit", "Nirvana", "Nevermind", 301920),
    ("Wonderwall", "Oasis", "(What's the Story) Morning Glory?", 258773),
    ("Do I Wanna Know?", "Arctic Monkeys", "AM", 272394),
    ("Feel Good Inc.", "Gorillaz", "Demon Days", 222640),
    ("Midnight City", "M83", "Hurry Up, We're Dreaming", 243960),
    ("Electric Feel", "MGMT", "Oracular Spectacular", 229640),
    ("Get Lucky", "Daft Punk", "Random Access Memories", 369626),
    ("One More Time", "Daft Punk", "Discovery", 320357),
    ("Titanium", "David Guetta & Sia", "Nothing but the Beat", 245040),
    ("Lose Yourself", "Eminem", "8 Mile", 326466),
    ("HUMBLE.", "Kendrick Lamar", "DAMN.", 177000),
    ("SICKO MODE", "Travis Scott", "ASTROWORLD", 312820),
    ("Gods Plan", "Drake", "Scorpion", 198973),
    ("Redbone", "Childish Gambino", "Awaken, My Love!", 326933),
    ("Pink + White", "Frank Ocean", "Blonde", 184516),
    ("Lost in Japan", "Shawn Mendes", "Shawn Mendes", 201120),
    ("Despacito", "Luis Fonsi & Daddy Yankee", "VIDA", 228827),
    ("Tití Me Preguntó", "Bad Bunny", "Un Verano Sin Ti", 243716),
    ("Hips Don't Lie", "Shakira", "Oral Fixation Vol. 2", 218093),
    ("Clair de Lune", "Claude Debussy", "Suite bergamasque", 302000),
    ("Weightless", "Marconi Union", "Weightless", 480000),
    ("Holocene", "Bon Iver", "Bon Iver", 336613),
    ("Skinny Love", "Bon Iver", "For Emma, Forever Ago", 238733),
    ("Riptide", "Vance Joy", "Dream Your Life Away", 204280),
]

# Playlist names per provider; each gets a random slice of the catalog.
PLAYLIST_NAMES: dict[ProviderType, list[tuple[str, str]]] = {
    ProviderType.SPOTIFY: [
        ("Daily Mix 1", "Made for you"),
        ("Workout Hits", "Keep the energy up"),
        ("Chill Evenings", "Low-key tracks to unwind"),
        ("Road Trip 2024", "Songs from the summer drive"),
        ("Liked Songs Archive", "Old liked songs"),
    ],
    ProviderType.APPLE_MUSIC: [
        ("Favourites", "Your all-time favourites"),
        ("Focus Flow", "Music to concentrate"),
        ("Throwback Classics", "Hits from the 70s to the 00s"),
        ("Party Starters", "Turn it up"),
    ],
    ProviderType.AMAZON_MUSIC: [
        ("My Discovery Mix", "New finds"),
        ("Rock Essentials", "Guitar anthems"),
        ("Sunday Morning", "Slow start"),
        ("Gym Session", "High tempo"),
    ],
}

# Title shown for songs that were pulled from the service's catalog
UNAVAILABLE_TITLE = "Track unavailable"
