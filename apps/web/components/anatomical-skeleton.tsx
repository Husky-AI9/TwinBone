import type { BoneSiteId } from "../lib/preview-data";

const BONE = "#e7efec";
const BONE_EDGE = "#9fb5af";
const JOINT = "#c6d7d2";
const SELECTED = "#2f766e";
const SELECTED_LIGHT = "#83b7ae";

export function AnatomicalSkeleton({ selected }: { selected: BoneSiteId }) {
  const siteStroke = (site: BoneSiteId) =>
    selected === site ? SELECTED : BONE_EDGE;
  const siteFill = (site: BoneSiteId) =>
    selected === site ? SELECTED_LIGHT : BONE;
  const boneLine = {
    fill: "none",
    stroke: BONE_EDGE,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
  };
  const ribs = [
    { y: 142, width: 52, drop: 10 },
    { y: 154, width: 61, drop: 14 },
    { y: 167, width: 67, drop: 18 },
    { y: 181, width: 70, drop: 22 },
    { y: 196, width: 67, drop: 25 },
    { y: 211, width: 61, drop: 27 },
    { y: 225, width: 52, drop: 27 },
  ];

  return (
    <svg
      role="img"
      aria-labelledby="skeleton-title skeleton-description"
      viewBox="0 0 360 695"
      className="h-[520px] w-full"
      preserveAspectRatio="xMidYMid meet"
    >
      <title id="skeleton-title">Anterior human skeletal site map</title>
      <desc id="skeleton-description">
        Anatomically structured front view showing the skull, thoracic cage,
        vertebral column, pelvis, arms, hands, legs, and feet. Selected bone
        density sites are highlighted.
      </desc>
      <defs>
        <linearGradient id="skeletal-bone" x1="0" x2="1" y1="0" y2="1">
          <stop stopColor="#fbfdfc" />
          <stop offset="0.58" stopColor={BONE} />
          <stop offset="1" stopColor="#cbdad6" />
        </linearGradient>
        <filter
          id="skeletal-shadow"
          x="-20%"
          y="-20%"
          width="140%"
          height="140%"
        >
          <feDropShadow
            dx="0"
            dy="2"
            stdDeviation="2.5"
            floodColor="#315f5a"
            floodOpacity=".12"
          />
        </filter>
      </defs>

      <g filter="url(#skeletal-shadow)">
        <g data-anatomy="skull">
          <path
            d="M149 30c8-14 20-21 31-21s23 7 31 21c7 12 8 32 3 48-3 11-10 20-17 27l-3 19-14 12-14-12-3-19c-7-7-14-16-17-27-5-16-4-36 3-48Z"
            fill="url(#skeletal-bone)"
            stroke={BONE_EDGE}
            strokeWidth="2"
          />
          <path
            d="M151 62c8-9 18-12 29-12s21 3 29 12"
            {...boneLine}
            strokeWidth="1.5"
          />
          <ellipse
            cx="164"
            cy="70"
            rx="10"
            ry="8"
            fill="#f4f8f6"
            stroke={BONE_EDGE}
            strokeWidth="1.5"
          />
          <ellipse
            cx="196"
            cy="70"
            rx="10"
            ry="8"
            fill="#f4f8f6"
            stroke={BONE_EDGE}
            strokeWidth="1.5"
          />
          <path
            d="m180 72-6 18h12l-6-18Z"
            fill="#f4f8f6"
            stroke={BONE_EDGE}
            strokeWidth="1.3"
          />
          <path
            d="M158 96c7 8 14 11 22 11s15-3 22-11l-3 19c-6 7-12 10-19 10s-13-3-19-10l-3-19Z"
            fill="#f1f6f4"
            stroke={BONE_EDGE}
            strokeWidth="1.6"
          />
          {[166, 173, 180, 187, 194].map((x) => (
            <line
              key={x}
              x1={x}
              x2={x}
              y1="104"
              y2="117"
              stroke={BONE_EDGE}
              strokeWidth="1"
            />
          ))}
        </g>

        <g data-anatomy="vertebral-column">
          {[0, 1, 2, 3, 4, 5, 6].map((index) => (
            <rect
              key={index}
              x="174"
              y={130 + index * 8}
              width="12"
              height="5"
              rx="2.5"
              fill={BONE}
              stroke={BONE_EDGE}
              strokeWidth="1"
            />
          ))}
          {[0, 1, 2, 3, 4, 5, 6, 7, 8].map((index) => (
            <rect
              key={index}
              x="172"
              y={189 + index * 9}
              width="16"
              height="6"
              rx="3"
              fill={BONE}
              stroke={BONE_EDGE}
              strokeWidth="1"
            />
          ))}
          <g data-site="lumbar-spine">
            {[0, 1, 2, 3, 4].map((index) => (
              <path
                key={index}
                d={`M169 ${274 + index * 12}h22l3 5-4 5h-20l-4-5 3-5Z`}
                fill={siteFill("lumbar-spine")}
                stroke={siteStroke("lumbar-spine")}
                strokeWidth="1.5"
              />
            ))}
          </g>
        </g>

        <g data-anatomy="pectoral-girdle">
          <path
            d="M178 145c-17-14-38-20-62-18-9 1-18 5-25 11"
            {...boneLine}
            strokeWidth="7"
          />
          <path
            d="M182 145c17-14 38-20 62-18 9 1 18 5 25 11"
            {...boneLine}
            strokeWidth="7"
          />
          <path
            d="M111 137c-17 9-25 29-20 53l28-15 18-31-26-7Z"
            fill={BONE}
            stroke={BONE_EDGE}
            strokeWidth="1.5"
          />
          <path
            d="M249 137c17 9 25 29 20 53l-28-15-18-31 26-7Z"
            fill={BONE}
            stroke={BONE_EDGE}
            strokeWidth="1.5"
          />
        </g>

        <g data-anatomy="thoracic-cage">
          {ribs.map((rib) => (
            <g key={rib.y}>
              <path
                d={`M175 ${rib.y}C${158 - rib.width / 3} ${rib.y - 7} ${180 - rib.width} ${rib.y + 1} ${180 - rib.width} ${rib.y + rib.drop}C${180 - rib.width} ${rib.y + rib.drop + 10} 152 ${rib.y + rib.drop + 8} 176 ${rib.y + rib.drop + 2}`}
                {...boneLine}
                strokeWidth="3.2"
              />
              <path
                d={`M185 ${rib.y}C${202 + rib.width / 3} ${rib.y - 7} ${180 + rib.width} ${rib.y + 1} ${180 + rib.width} ${rib.y + rib.drop}C${180 + rib.width} ${rib.y + rib.drop + 10} 208 ${rib.y + rib.drop + 8} 184 ${rib.y + rib.drop + 2}`}
                {...boneLine}
                strokeWidth="3.2"
              />
            </g>
          ))}
          <path
            d="M180 143c-5 8-6 23-4 42l4 68 4-68c2-19 1-34-4-42Z"
            fill={BONE}
            stroke={BONE_EDGE}
            strokeWidth="1.5"
          />
        </g>

        <g data-anatomy="pelvis">
          <path
            d="M176 329c-18-18-42-22-61-10-13 8-21 23-18 39 3 19 19 37 43 51l29-23 7-57Zm-59 10c16-8 31-4 42 9l-13 35c-17-7-29-18-34-31-2-5 0-10 5-13Z"
            fill={BONE}
            fillRule="evenodd"
            stroke={BONE_EDGE}
            strokeWidth="2"
          />
          <g data-site="left-total-hip">
            <path
              d="M184 329c18-18 42-22 61-10 13 8 21 23 18 39-3 19-19 37-43 51l-29-23-7-57Zm59 10c-16-8-31-4-42 9l13 35c17-7 29-18 34-31 2-5 0-10-5-13Z"
              fill={siteFill("left-total-hip")}
              fillRule="evenodd"
              stroke={siteStroke("left-total-hip")}
              strokeWidth="2"
            />
          </g>
          <path
            d="M169 331h22l10 47-21 22-21-22 10-47Z"
            fill="#d8e4e0"
            stroke={BONE_EDGE}
            strokeWidth="1.5"
          />
          <ellipse
            cx="145"
            cy="394"
            rx="12"
            ry="10"
            fill="#f4f8f6"
            stroke={BONE_EDGE}
            strokeWidth="2"
          />
          <ellipse
            cx="215"
            cy="394"
            rx="12"
            ry="10"
            fill="#f4f8f6"
            stroke={siteStroke("left-total-hip")}
            strokeWidth="2"
          />
        </g>

        <g data-anatomy="upper-limbs">
          <circle
            cx="93"
            cy="143"
            r="9"
            fill={JOINT}
            stroke={BONE_EDGE}
            strokeWidth="2"
          />
          <circle
            cx="267"
            cy="143"
            r="9"
            fill={JOINT}
            stroke={BONE_EDGE}
            strokeWidth="2"
          />
          <path d="M91 151c-5 35-8 67-7 97" {...boneLine} strokeWidth="12" />
          <path d="M269 151c5 35 8 67 7 97" {...boneLine} strokeWidth="12" />
          <circle
            cx="84"
            cy="253"
            r="8"
            fill={JOINT}
            stroke={BONE_EDGE}
            strokeWidth="2"
          />
          <circle
            cx="276"
            cy="253"
            r="8"
            fill={JOINT}
            stroke={BONE_EDGE}
            strokeWidth="2"
          />
          <path d="M80 260 66 356M88 260l-4 98" {...boneLine} strokeWidth="6" />
          <g data-site="forearm">
            <path
              d="m272 260 4 98m4-98 14 96"
              fill="none"
              stroke={siteStroke("forearm")}
              strokeWidth="6"
              strokeLinecap="round"
            />
          </g>
          <g data-anatomy="hands" {...boneLine} strokeWidth="3">
            <path d="M64 361 55 389m17-29-5 34m13-34 1 34m7-33 7 31m200-41 9 28m-17-29 5 34m-13-34-1 34m-7-33-7 31" />
            <path
              d="m55 389-9 22m21-17-4 23m18-23 1 24m13-26 7 21m202-24 9 22m-21-17 4 23m-18-23-1 24m-13-26-7 21"
              strokeWidth="2.4"
            />
          </g>
        </g>

        <g data-anatomy="lower-limbs">
          <g data-anatomy="femur">
            <path
              d="M126 405c-9 3-13 13-8 22l23 112c2 9 0 14-4 20l17 5 18-5c-5-6-8-12-9-20l-21-111c2-10-5-21-16-23Z"
              fill="url(#skeletal-bone)"
              stroke={BONE_EDGE}
              strokeWidth="2"
            />
            <path
              d="M234 405c9 3 13 13 8 22l-23 112c-2 9 0 14 4 20l-17 5-18-5c5-6 8-12 9-20l21-111c-2-10 5-21 16-23Z"
              fill="url(#skeletal-bone)"
              stroke={BONE_EDGE}
              strokeWidth="2"
            />
            <path d="M145 397c-8 0-14 4-20 13" {...boneLine} strokeWidth="12" />
            <g data-site="femoral-neck">
              <path
                d="M215 397c8 0 14 4 20 13"
                fill="none"
                stroke={siteStroke("femoral-neck")}
                strokeWidth="12"
                strokeLinecap="round"
              />
            </g>
            <circle
              cx="123"
              cy="415"
              r="8"
              fill={BONE}
              stroke={BONE_EDGE}
              strokeWidth="2"
            />
            <circle
              cx="237"
              cy="415"
              r="8"
              fill={BONE}
              stroke={BONE_EDGE}
              strokeWidth="2"
            />
          </g>

          <g data-anatomy="patella">
            <path
              d="M146 555c2-7 7-10 13-9 6 1 9 6 8 13-1 8-5 13-11 15-7-2-11-9-10-19Z"
              fill={JOINT}
              stroke={BONE_EDGE}
              strokeWidth="2"
            />
            <path
              d="M214 555c-2-7-7-10-13-9-6 1-9 6-8 13 1 8 5 13 11 15 7-2 11-9 10-19Z"
              fill={JOINT}
              stroke={BONE_EDGE}
              strokeWidth="2"
            />
          </g>

          <g data-anatomy="tibia">
            <path
              d="M146 570c-4 5-4 13 0 18l2 55-5 15 15 6 10-8-6-14 2-55c4-6 3-13-2-17h-16Z"
              fill="url(#skeletal-bone)"
              stroke={BONE_EDGE}
              strokeWidth="2"
            />
            <path
              d="M214 570c4 5 4 13 0 18l-2 55 5 15-15 6-10-8 6-14-2-55c-4-6-3-13 2-17h16Z"
              fill="url(#skeletal-bone)"
              stroke={BONE_EDGE}
              strokeWidth="2"
            />
            <path d="m154 587 1 58" stroke="#b3c6c1" strokeWidth="1.5" />
            <path d="m206 587-1 58" stroke="#b3c6c1" strokeWidth="1.5" />
          </g>

          <g data-anatomy="fibula">
            <path
              d="M139 576c-4 20-6 45-6 70l-3 11"
              {...boneLine}
              strokeWidth="5"
            />
            <path
              d="M221 576c4 20 6 45 6 70l3 11"
              {...boneLine}
              strokeWidth="5"
            />
            <circle
              cx="138"
              cy="576"
              r="4"
              fill={BONE}
              stroke={BONE_EDGE}
              strokeWidth="1.5"
            />
            <circle
              cx="222"
              cy="576"
              r="4"
              fill={BONE}
              stroke={BONE_EDGE}
              strokeWidth="1.5"
            />
          </g>

          <g data-anatomy="feet">
            <g data-anatomy="tarsals">
              <path
                d="M131 654c7-4 17-3 27 4l2 12-14 7-18-9 3-14Z"
                fill={BONE}
                stroke={BONE_EDGE}
                strokeWidth="1.5"
              />
              <path
                d="M229 654c-7-4-17-3-27 4l-2 12 14 7 18-9-3-14Z"
                fill={BONE}
                stroke={BONE_EDGE}
                strokeWidth="1.5"
              />
            </g>
            <g {...boneLine} strokeWidth="3">
              <path d="m145 669-27 8m34-6-21 8m28-5-14 7m70-12 27 8m-34-6 21 8m-28-5 14 7" />
              <path
                d="m118 677-12 1m25 1-10 4m24-2-8 5m105-9 12 1m-25 1 10 4m-24-2 8 5"
                strokeWidth="2.3"
              />
            </g>
            <path
              d="M129 657c-5 6-11 12-19 17M231 657c5 6 11 12 19 17"
              {...boneLine}
              strokeWidth="4"
            />
          </g>
        </g>
      </g>
    </svg>
  );
}
