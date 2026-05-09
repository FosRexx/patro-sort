require Time::Local;

%Image::ExifTool::UserDefined = (
  'Image::ExifTool::Composite' => {
    MyDate => {
    # A highly curated list of legitimate creation dates across all media types.
    # This acts like a safe, filesystem-free version of -time:all.
      Desire => {
        0  => 'Quicktime:CreationDate',       # MOV/MP4 - local time with TZ
        1  => 'Keys:CreationDate',            # Apple iOS video
        2  => 'EXIF:DateTimeOriginal',        # EXIF best
        3  => 'EXIF:CreateDate',              # EXIF digitized
        4  => 'EXIF:ModifyDate',              # EXIF fallback
        5  => 'Quicktime:CreateDate',         # MOV/MP4 UTC base
        6  => 'Quicktime:TrackCreateDate',    # MOV/MP4 track fallback
        7  => 'Quicktime:MediaCreateDate',    # MOV/MP4 media fallback
        8  => 'XMP-exif:DateTimeOriginal',    # XMP EXIF
        9  => 'XMP-xmp:CreateDate',           # XMP basic
        10 => 'XMP-photoshop:DateCreated',    # Photoshop/Lightroom
        11 => 'IPTC:DateTimeCreated',         # IPTC composite
        12 => 'PNG:CreationTime',             # PNG standard
        13 => 'ID3:RecordingTime',            # MP3
        14 => 'RIFF:DateTimeOriginal',        # AVI / WAV
        15 => 'XMP-dc:Date',                  # Dublin Core
        16 => 'ID3:Year',                     # MP3 fallback (year only)
      },
      Groups    => { 2 => 'Time' },
      ValueConv => q{
        my @valid_epochs;

        for my $date (@val) {
          # Skip missing or empty values
          next unless defined $date;
          $date =~ s/^\s+|\s+$//g;
          next if $date eq '';
          
          # Skip broken zero-dates (e.g., 0000:00:00 00:00:00)
          next if $date =~ /^0+[:\/\s0]*$/;
          
          # Skip default Epoch anomalies often caused by unset hardware clocks
          next if $date =~ /^1904:01:01 00:00:00/; # Apple/QuickTime epoch
          next if $date =~ /^1970:01:01 00:00:00/; # Unix epoch

          # Remove fractional seconds to simplify regex parsing
          (my $clean_date = $date) =~ s/(\d{2})\.(\d+)(Z|[+-]|$)/$1$3/;

          my ($yr,$mo,$dy,$hr,$mn,$sc,$tz,$sign,$tzh,$tzm);
          
          # Full YYYY:MM:DD HH:MM:SS format with optional timezone
          if ($clean_date =~ /^(\d{4}):(\d{2}):(\d{2}) (\d{2}):(\d{2}):(\d{2})(Z|([+-])(\d{2}):(\d{2}))?$/) {
            ($yr,$mo,$dy,$hr,$mn,$sc,$tz,$sign,$tzh,$tzm) = ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10);
          } 
          # Year-only format (e.g., ID3 tags)
          elsif ($clean_date =~ /^(\d{4})$/) {
            ($yr,$mo,$dy,$hr,$mn,$sc) = ($1, 1, 1, 0, 0, 0);
          } else {
            next; # Skip unrecognized formats
          }

          # Calculate explicit timezone offset in seconds
          my $offset_secs = 0;
          if ($tz && $tz ne 'Z') {
            $offset_secs = ($tzh * 3600 + $tzm * 60) * ($sign eq '+' ? -1 : 1);
          }

          # Convert to UTC Epoch. We wrap in eval{} to catch impossible dates 
          # (like 2024:15:45) without crashing the Perl script.
          my $epoch = eval { Time::Local::timegm($sc, $mn, $hr, $dy, $mo - 1, $yr - 1900) };
          next if $@; 

          # Adjust by offset so all epochs represent true UTC absolute time
          $epoch += $offset_secs;
          push @valid_epochs, $epoch;
        }

        return undef unless @valid_epochs;

        # Sort the valid dates ascending (oldest first)
        @valid_epochs = sort { $a <=> $b } @valid_epochs;
        my $oldest_epoch = $valid_epochs[0];

        # Return a cleanly formatted ISO 8601 UTC string
        my @u = gmtime($oldest_epoch);
        return sprintf("%04d-%02d-%02dT%02d:%02d:%02dZ",
          $u[5] + 1900, $u[4] + 1, $u[3], $u[2], $u[1], $u[0]);
      },
    },
  },
);
