"""Cover direction for new productions; existing styles stay unchanged."""
def family_poster_prompt(j):
    language=j['config'].get('language','Deutsch (de-DE)')
    cast='\n'.join(c['name']+': '+c['appearance'] for c in j['characters'])
    return f"""Generate ONE finished premium 3D animated family-mystery drama poster for a TikTok cover. Portrait 9:16, preferably 1080x1920 or higher. ALL visible words must be in {language}, with native spelling and accents.
Story: {j['title']}.
Opening conflict: {j['scenes'][0]['meaning']}.
Full story context: {' '.join(scene['meaning'] for scene in j['scenes'])}
Headline idea: {j['script']['cover_title']}. Use 3 to 8 words on at most three lines; shorten naturally for mobile legibility. A concrete secret, unusual object or dilemma from THIS story, without revealing its resolution. No invented years, numbers, relatives, pregnancy or betrayal absent from the story. No guaranteed outcome or false claim.
Reference image 1 supplies the actual story characters and identities. Reference image 2, if attached, is a PHONE SCREENSHOT OF A GRID of approved poster styles, NOT an image to reproduce. Study the individual thumbnails for composition and typography only. Output a single poster: never a phone screenshot, grid, collage of thumbnails, profile page or TikTok interface. Do not reproduce its titles, characters, usernames, counts, pinned badges or watermarks.
Preserve the exact story cast, age, fruit identity and clothing:
{cast}
Composition: very large expressive faces, worried or shocked protagonist and a supporting or opposing character when relevant. Make the story's real mystery object or revealing gesture clearly visible in the central area. Warm golden cinematic light, rich fruit textures, detailed costumes, softly focused story setting. Stage a family melodrama or mystery according to the actual plot; do not force family relationships on unrelated stories.
Typography: HUGE bold condensed display serif lettering in warm yellow/gold, strong dark outline and restrained shadow, similar to a dramatic storybook or serial-drama poster. Place the headline in the UPPER area, within approximately 12 to 35 percent of image height and central 84 percent of width. Reserve space for the title above faces; keep eyes and expressions unobstructed and important objects readable. Keep the bottom 20 percent free of crucial text. Legible when reduced to a small profile thumbnail. No extra labels, episode number, logos, arrows or large empty floor. Produce the final cover image now, not instructions.
"""
