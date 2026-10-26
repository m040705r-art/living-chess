// Moonlit night sky for the ruin stage (skybox material, Built-in RP): a dark gradient, a full moon with a
// soft halo and faint maria, and a sparse twinkling star field. All procedural, one cheap pass.
Shader "Chess/NightSky"
{
    Properties
    {
        _Top ("Zenith", Color) = (0.012, 0.018, 0.045, 1)
        _Horizon ("Horizon", Color) = (0.06, 0.075, 0.12, 1)
        _MoonDir ("Moon Direction", Vector) = (-0.45, 0.42, 0.79, 0)
        _MoonColor ("Moon Color", Color) = (1, 0.96, 0.86, 1)
        _MoonSize ("Moon Radius (rad)", Float) = 0.045
        _Halo ("Halo", Float) = 0.35
        _Stars ("Stars", Float) = 1
    }
    SubShader
    {
        Tags { "Queue" = "Background" "RenderType" = "Background" "PreviewType" = "Skybox" }
        Cull Off ZWrite Off

        Pass
        {
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #include "UnityCG.cginc"

            fixed4 _Top, _Horizon, _MoonColor;
            float4 _MoonDir;
            float _MoonSize, _Halo, _Stars;

            struct v2f { float4 pos : SV_POSITION; float3 dir : TEXCOORD0; };

            v2f vert(appdata_base v)
            {
                v2f o;
                o.pos = UnityObjectToClipPos(v.vertex);
                o.dir = v.vertex.xyz;
                return o;
            }

            float hash(float3 p)
            {
                p = frac(p * 0.3183099 + 0.1); p *= 17.0;
                return frac(p.x * p.y * p.z * (p.x + p.y + p.z));
            }

            fixed4 frag(v2f i) : SV_Target
            {
                float3 d = normalize(i.dir);
                float h = saturate(d.y);
                float3 c = lerp(_Horizon.rgb, _Top.rgb, sqrt(h));
                if (d.y < 0) c = _Horizon.rgb;   // under the horizon only fog-coloured ground shows anyway

                // stars: one candidate per cell of a cube grid, thinned out, fading towards the horizon
                float3 cell = floor(d * 160);
                float s = hash(cell);
                float3 sp = (cell + 0.5 + (float3(hash(cell + 3.1), hash(cell + 7.7), hash(cell + 1.3)) - 0.5) * 0.6) / 160;
                float star = step(0.985, s) * smoothstep(0.004, 0.0, distance(d, normalize(sp)));
                star *= (0.6 + 0.4 * sin(_Time.y * (2 + s * 5) + s * 50)) * smoothstep(0.05, 0.35, d.y);
                c += star * _Stars;

                // the moon: halo, then the disc with faint darker maria
                float3 m = normalize(_MoonDir.xyz);
                float ang = acos(clamp(dot(d, m), -1, 1));
                c += _MoonColor.rgb * (_Halo * exp(-ang * 9) + 0.06 * exp(-ang * 2.5));
                float disc = smoothstep(_MoonSize, _MoonSize * 0.92, ang);
                float3 q = (d - m) / _MoonSize * 3;
                float maria = hash(floor(q * 1.7)) * 0.12 + hash(floor(q * 3.3)) * 0.06;
                c = lerp(c, _MoonColor.rgb * (1.1 - maria), disc);
                return fixed4(c, 1);
            }
            ENDCG
        }
    }
}
