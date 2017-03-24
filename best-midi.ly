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
  r16 e''4 ais, b16 cis b8 a4 fis a d2 fis8 a d, cis e g4. fis8 
  e fis e cis e cis d b e d g a4 g8 gis16 
  | % 6
  g fis8 e fis e4 fis8 e b a fis gis4 a2 b8 d b4 d4. e8 d cis 
  d fis d4 b b'8 a g fis e4 fis g8 d e a, g fis a a' a,16 gis' 
  a,8 g4 d' b16*5 a8. b8 a fis'4. e8 d4 fis e <g,, b d, > a2. d4 
  c'8 b d,4 g d'2. e8 fis g4 gis8 fis16 e16*5 cis8 d <a, cis, e >16 
  <c, e g > <a' cis, e >8*7 fis''8 g fis d4 b8 a d e d a d a fis' 
  g g, e'4 cis8 b cis4. d8 f16 fis e8 d cis d e d16*11 fis16 e8 
  cis d8. e16 g4 e a1 g8 e cis4 d2 fis4 d2 a'4 gis8 fis e cis fis4 
  cis8 b4 e8 g, a4 d8 e g cis, e d4 fis d8 cis a b d e g a g16 
  a fis8 a g e d4 b8 
}



trackB = <<
  \context Voice = voiceA \trackBchannelB
  \context Voice = voiceB \trackBchannelBvoiceB
  \context Voice = voiceC \trackBchannelBvoiceC
>>


\score {
  <<
    \context Staff=trackB \trackA
    \context Staff=trackB \trackB
  >>
  \layout {}
  \midi {}
}
