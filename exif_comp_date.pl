require Time::Local;

%Image::ExifTool::UserDefined = (
  'Image::ExifTool::Composite' => {
    MyDate => {
      Desire => {
        0  => 'Quicktime:CreateDate',          # MOV/MP4 — UTC, no offset stored
        1  => 'Quicktime:CreationDate',        # MOV/MP4 — local time with timezone
        2  => 'EXIF:DateTimeOriginal',         # EXIF best — when shutter fired
        3  => 'EXIF:CreateDate',               # EXIF digitized date
        4  => 'EXIF:ModifyDate',               # EXIF last modified (fallback)
        5  => 'IPTC:DateTimeCreated',          # IPTC
        6  => 'XMP-exif:DateTimeOriginal',     # XMP EXIF
        7  => 'XMP-xmp:CreateDate',            # XMP basic
        8  => 'XMP-photoshop:DateCreated',     # Photoshop / Lightroom
        9  => 'XMP-dc:Date',                   # Dublin Core
        10 => 'PNG:CreationTime',              # PNG
        11 => 'ID3:RecordingTime',             # MP3
        12 => 'ID3:Year',                      # MP3 fallback (year only)
        # 13 => 'FileModifyDate',                # Filesystem modify date
        # 14 => 'FileCreateDate',                # Filesystem create date
      },
      Groups    => { 2 => 'Time' },
      ValueConv => q{
        # Null out bogus zero dates and empty strings
        for my $i (0..$#val) {
          next unless defined $val[$i];
          $val[$i] = undef if $val[$i] eq '';
          $val[$i] = undef if $val[$i] =~ /^0+[:\/\s0]*$/;
        }

        # Priority: timezone-aware sources first, then UTC sources, then fallbacks
        # $val[1]  Quicktime:CreationDate  — has TZ, most trustworthy for video
        # $val[2]  EXIF:DateTimeOriginal   — best for photos
        # $val[0]  Quicktime:CreateDate    — UTC already (no TZ stored), good quality
        # ...then the rest in descending reliability
        my $best =
          $val[1]  || $val[2]  || $val[3]  || $val[0]  ||  # top-tier
          $val[4]  || $val[5]  || $val[6]  || $val[7]  ||  # good fallbacks
          $val[8]  || $val[9]  || $val[10] || $val[11] ||  # format-specific
          $val[12];
          # $val[13] || $val[14];                 # last resorts

        return undef unless defined $best;

        # Handle fractional seconds by stripping them before parsing,
        # then reattaching (keeps sub-second info if present)
        my $frac = '';
        (my $best_clean = $best) =~ s/(\d{2})\.(\d+)(Z|[+-]|$)/$1$3/ && ($frac = ".$2");
        # Note: $frac captured but we drop it — UTC output is whole seconds.
        # Change sprintf below if you need milliseconds.

        # Full datetime with optional timezone
        if ($best_clean =~ /^(\d{4}):(\d{2}):(\d{2}) (\d{2}):(\d{2}):(\d{2})(Z|([+-])(\d{2}):(\d{2}))?$/) {
          my ($yr,$mo,$dy,$hr,$mn,$sc,$tz,$sign,$tzh,$tzm) = ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10);

          if ($tz && $tz ne 'Z') {
            # Explicit UTC offset — convert to UTC
            # timegm() interprets args as UTC; our values are local, so the
            # resulting epoch is off by the offset — we correct by adding it back.
            my $offset_secs = ($tzh * 3600 + $tzm * 60) * ($sign eq '+' ? -1 : 1);
            my $epoch = Time::Local::timegm($sc, $mn, $hr, $dy, $mo - 1, $yr - 1900);
            $epoch += $offset_secs;
            my @u = gmtime($epoch);
            return sprintf("%04d-%02d-%02dT%02d:%02d:%02dZ",
              $u[5] + 1900, $u[4] + 1, $u[3], $u[2], $u[1], $u[0]);
          } else {
            # No offset or already Z (e.g. Quicktime:CreateDate is stored as UTC)
            return sprintf("%04d-%02d-%02dT%02d:%02d:%02dZ", $yr, $mo, $dy, $hr, $mn, $sc);
          }
        }

        # Year-only (e.g. ID3:Year) — Jan 1 midnight UTC
        if ($best =~ /^(\d{4})$/) {
          return sprintf("%04d-01-01T00:00:00Z", $1);
        }

        return $best;  # unrecognized format — pass through as-is
      },
    },
  },
);
