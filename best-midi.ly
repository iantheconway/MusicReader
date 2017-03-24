% Lily was here -- automatically converted by midi2ly.py from best.midi
\version "2.14.0"

\layout {
  \context {
    \Voice
    \remove "Note_heads_engraver"
    \consists "Completion_heads_engraver"
    \remove "Rest_engraver"
    \consists "Completion_rest_engraver"
  }
}

trackAchannelA = {
  
  \time 4/4 
  
}

trackA = <<
  \context Voice = voiceA \trackAchannelA
>>


trackBchannelB = \relative c {
  \voiceOne
  r16 <g' b d, >4 <d fis a >4*5 d''4 g fis8 g fis e d e a g e g 
  e d e d e c a4. f8 gis e' <a, c,, e g >16 gis a8*5 g8 fis4 e8 
  d4 a' d8 fis d4 fis8 a b a fis16 gis a8 cis, d cis b fis e cis' 
  e, a4 b8 cis d cis b d fis e d b a4 b8 cis e d e a, e' cis d 
  cis a4 cis a e e'8 a, b4 d8 a <d,, fis a >2 fis'4 b8 cis fis, 
  b a' a,4 cis8 a <fis fis, a cis, >4. <a b, dis, fis >16 <fis, a cis, > 
  <b dis, fis >8*25 b'8 a cis b4. e,4 a cis8 d e cis r8 e, cis'4 
  a8 b a b a gis a4 b a cis a e'8 d cis4 a2 b4 a cis8 d e fis4. 
  cis4 b8 a2 cis8 d4 a gis8 a16 b a2 e'8 a,4. cis8 b a b d fis 
  e4 fis8*5 e8 fis4 e cis8 e g fis16*5 e8. cis8 a b cis e 
}

trackBchannelBvoiceB = \relative c {
  \voiceTwo
  r16 d''2. r4 a8 d e4 <g,, b d, >2. <a c, e >4*5 <c, e g >1 <a' cis, e >4 
  r16 <a cis, e >16*11 <d, fis a >1*2 <e gis b >2. <a cis, e >8*23 
  <b d, fis >8*5 <a cis, e >4*7 r16 a''8. a,4 <b, d, fis >2. <fis a cis, >16*9 
  <b d, fis >16 r16*7 b'8 
  | % 17
  a16 gis8 b a4. cis8 e cis b4 a16 gis b8 a4 cis8 b a b a4 b8 
  a b a <e, gis b >1 <a cis, e > <d, fis a >1. <e gis b >1 <a cis, e >4*5 
  <d, fis a >2*5 <fis a cis, >1 <d fis a >2 <a' cis, e > <d, fis a >1 
  <a' cis, e >4*7 
}

trackB = <<
  \context Voice = voiceA \trackBchannelB
  \context Voice = voiceB \trackBchannelBvoiceB
>>


\score {
  <<
    \context Staff=trackB \trackA
    \context Staff=trackB \trackB
  >>
  \layout {}
  \midi {}
}
